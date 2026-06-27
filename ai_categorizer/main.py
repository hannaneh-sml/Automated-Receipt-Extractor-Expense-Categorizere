import pika
import json
import time
from supabase_client import SupabaseClient
from agent_brain import AgentBrain
from config import settings
import time

QUEUE_NAME = "llm_task_queue"

db_client = SupabaseClient()
brain = AgentBrain(db_client)

def process_agent_workflow(ch, method, properties, body):
    payload = json.loads(body)
    job_id = payload.get("job_id")
    extracted_text = payload.get("extracted_text")
    user_prompt = payload.get("user_prompt")
    
    print(f"\n⚡ [AGENT ENGINE] Ingesting Job: {job_id}")

    print("⏳ Giving system CPU 5 seconds to recover from OCR...")
    time.sleep(5)

    metadata = brain.extract_receipt_metadata(extracted_text)
    if not metadata or not metadata.get("amount"):
        print("❌ [ABORTED] Phi-3:mini failed to safely isolate financial fields from raw text.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    merchant = metadata.get("merchant", "Unknown Merchant")
    amount = float(metadata.get("amount"))
    date = metadata.get("date") or time.strftime("%Y-%m-%d")
    implied_cat = metadata.get("implied_category")

    print(f"🔍 Extracted Data -> Merchant: {merchant} | Amount: {amount} | Date: {date}")

    # Step 2: Determine categorization
    user_cat = None
    if "groceries" in user_prompt.lower(): user_cat = "Groceries"
    elif "transport" in user_prompt.lower(): user_cat = "Transport"

    final_category = brain.infer_category_or_abort(merchant, user_cat, implied_cat)
    
    if final_category is None:
        print(f"❌ [ABORTED] Categorization remains completely ambiguous for '{merchant}'. Blocking record insertion.")
    else:
        # Step 3: Persist to cloud database
        db_client.add_expense(date, merchant, amount, final_category)
    
    # Step 4: Execute RAG/Analytical query questions
    if any(keyword in user_prompt.lower() for keyword in ["how much", "spent", "total", "calculate"]):
        print("📊 Running transactional dynamic lookup query...")
        answer = brain.answer_financial_question(user_prompt)
        print(f"\n💬 [AI Response]:\n{answer}\n")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_services():
    connection = pika.BlockingConnection(pika.ConnectionParameters(settings.rabbitmq_host))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_agent_workflow)
    
    print(f"🎧 AI Agent Online. Monitoring queue: '{QUEUE_NAME}'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_services()