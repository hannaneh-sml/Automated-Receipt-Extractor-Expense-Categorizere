import json
import time
from typing import Optional, Dict, Any
from openai import OpenAI
from config import settings


class AgentBrain:
    def __init__(self, db_client):
        self.db = db_client
        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.avalai.ir/v1"
        )
        self.model = "deepseek-v3.2"

    def extract_receipt_metadata(self, raw_ocr_text: str) -> Optional[Dict[str, Any]]:
        prompt = f"""
        You are a precise data extraction engine. Analyze the following raw OCR text from a receipt and extract the structured information.
        
        --- RAW OCR TEXT ---
        {raw_ocr_text}
        --------------------

        Extract exactly these four fields:
        1. merchant: The name of the store or company (e.g., "East Repair Inc").
        2. amount: The final total paid amount as a float number. Look closely at "Receipt Total", "Total", or the largest value. Do not include currency symbols ($).
        3. date: The receipt date converted into YYYY-MM-DD format. If ambiguous, use the best match.
        4. implied_category: Based on the descriptions or merchant, guess a logical expense category (e.g., "Transport", "Groceries", "Utilities", "Maintenance").

        Respond ONLY with a valid JSON block matching this structure:
        {{
            "merchant": string or null,
            "amount": float or null,
            "date": string or null,
            "implied_category": string or null
        }}
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Using Groq's JSON mode guarantees a perfect JSON object response
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{'role': 'user', 'content': prompt}],
                    response_format={"type": "json_object"} 
                )
                
                clean_content = response.choices[0].message.content.strip()
                return json.loads(clean_content)
                
            except json.JSONDecodeError:
                print(f"❌ Parsing Error: Model returned invalid JSON. Raw output:\n{clean_content}")
                return None 
                
            except Exception as e:
                print(f"⚠️ API Error (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2) 
                else:
                    print("❌ [ABORTED] Groq API failed to recover.")
                    return None

    def infer_category_or_abort(self, merchant: str, user_specified_category: Optional[str], fallback_suggestion: Optional[str]) -> Optional[str]:
        if user_specified_category and user_specified_category.strip():
            return user_specified_category.strip()

        history = self.db.get_all_expenses()
        history_str = json.dumps(history, ensure_ascii=False)

        prompt = f"""
        You are a financial accounting agent. Determine the absolute category for a transaction at merchant: "{merchant}".
        The model suggested a guess of "{fallback_suggestion}".
        
        Historical ledger data for comparison:
        {history_str}

        Respond ONLY with a valid JSON object matching this structure:
        {{
            "can_determine": true or false,
            "category": "CategoryName" or null,
            "reasoning": "Brief explanation"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            if result.get("can_determine") and result.get("category"):
                return result.get("category")
        except Exception as e:
            print(f"⚠️ Categorization inference failed: {e}")
        
        # Fallback to the initial guess if history is empty or inconclusive
        return fallback_suggestion if fallback_suggestion else None

    def answer_financial_question(self, user_question: str) -> str:
        history = self.db.get_all_expenses()
        history_str = json.dumps(history, ensure_ascii=False)

        prompt = f"""
        You are a financial analyst tracking expenses. Review the database ledger rows:
        {history_str}

        Answer this question accurately based only on data sums and dates inside the ledger.
        
        Question: {user_question}
        """
        try:
            # We don't use json_object format here because we want a conversational text answer
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error executing analysis: {str(e)}"