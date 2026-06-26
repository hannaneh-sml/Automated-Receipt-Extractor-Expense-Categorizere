import json
import ollama
from typing import Optional

class AgentBrain:
    def __init__(self, db_client):
        self.db = db_client 

    def infer_category_or_abort(self, merchant: str, user_specified_category: Optional[str]) -> Optional[str]:
        if user_specified_category and user_specified_category.strip():
            return user_specified_category.strip()

        history = self.db.get_all_expenses()
        history_str = json.dumps(history, ensure_ascii=False)

        prompt = f"""
        You are a financial accounting agent. Your task is to categorize a purchase.
        The user bought something from the merchant: "{merchant}".
        The user did not specify a category.

        Here is the historical transaction data from their database:
        {history_str}

        Based strictly on history, can you definitively match this merchant to a category?
        Respond ONLY with a valid JSON object matching this structure:
        {{
            "can_determine": true or false,
            "category": "CategoryName" or null,
            "reasoning": "Brief explanation"
        }}
        """
        try:
            response = ollama.chat(model='phi3:mini', messages=[{'role': 'user', 'content': prompt}])
            result = json.loads(response['message']['content'].strip())
            
            if result.get("can_determine"):
                return result.get("category")
        except Exception as e:
            print(f"⚠️ Categorization parsing failed. Error: {e}")
        
        return None

    def answer_financial_question(self, user_question: str) -> str:
        history = self.db.get_all_expenses()
        history_str = json.dumps(history, ensure_ascii=False)

        prompt = f"""
        You are a financial analyst looking at the user's expense database:
        {history_str}

        Answer the following question accurately based ONLY on the data provided. 
        If it involves math, calculate it step-by-step.
        
        Question: {user_question}
        """
        try:
            response = ollama.chat(model='phi3', messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content']
        except Exception as e:
            return f"Error executing financial query analysis: {str(e)}"