import pika
import json
import time
from dotenv import load_dotenv
from supabase_client import SupabaseClient
from agent_brain import AgentBrain

# Load environment variables FIRST
load_dotenv()

QUEUE_NAME = "llm_task_queue"

# Initialize our components
db_client = SupabaseClient()
brain = AgentBrain(db_client)

def process_agent_workflow(ch, method, properties, body):
    payload = json.loads(body)
    job_id = payload.get("job_id")
    extracted_text = payload.get("extracted_text")
    user_prompt = payload.get("user_prompt")
    
    print(f"\n⚡ [AGENT ENGINE] Processing task for Job: {job_id}")

    # TODO: In a later step, we will have Phi-3 extract these variables from 'extracted_text'
    # For now, we mock the extraction to test the database pipeline
    merchant_detected = "Ofogh Koorosh" 
    amount_detected = 185000.0
    current_date = time.strftime("%Y-%m-%d")
    
    user_cat = None
    if "groceries" in user_prompt.lower(): user_cat = "Groceries"
    elif "transport" in user_prompt.lower(): user_cat = "Transport"

    final_category = brain.infer_category_or_abort(merchant_detected, user_cat)
    
    if final_category is None:
        print(f"❌ [ABORTED] Could not classify expense for '{merchant_detected}'.")
    else:
        # Save to Supabase!
        db_client.add_expense(current_date, merchant_detected, amount_detected, final_category)
    
    if "how much" in user_prompt.lower() or "spent" in user_prompt.lower():
        print("🔍 Executing database analysis...")
        answer = brain.answer_financial_question(user_prompt)
        print(f"\n💬 [AI Response]:\n{answer}\n")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_services():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_agent_workflow)
    
    print(f"🎧 AI Agent Online. Monitoring queue: '{QUEUE_NAME}'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_services()