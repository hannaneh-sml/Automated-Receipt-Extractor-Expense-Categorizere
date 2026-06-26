import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("⚠️ Supabase credentials missing from .env! Running in Mock Mode.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)

    def get_all_expenses(self):
        """Fetches all rows from the expenses table."""
        if not self.supabase:
            return [{"date": "2026-06-01", "merchant": "Ofogh", "amount": 120000, "category": "Groceries"}]
        
        try:
            response = self.supabase.table("expenses").select("*").execute()
            return response.data  # Returns a clean list of dictionaries
        except Exception as e:
            print(f"❌ Supabase Read Error: {e}")
            return []

    def add_expense(self, date: str, merchant: str, amount: float, category: str):
        if not self.supabase:
            print(f"💾 [MOCK MODE] Inserted row: {merchant} - {amount}")
            return True
        
        try:
            self.supabase.table("expenses").insert({
                "date": date,
                "merchant": merchant,
                "amount": amount,
                "category": category
            }).execute()
            print("📊 Successfully appended record to Supabase!")
            return True
        except Exception as e:
            print(f"❌ Supabase Write Error: {e}")
            return False