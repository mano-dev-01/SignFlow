from main import app, db, User

def view_users():
    with app.app_context():
        users = User.query.all()
        if not users:
            print("\nNo users found in the database yet.")
            return
        
        print("\n" + "="*80)
        print(f"{'ID':<4} | {'Plan':<6} | {'Status':<9} | {'Name':<18} | {'Email':<28} | {'Google Linked'}")
        print("-" * 80)
        for user in users:
            linked = 'yes' if user.google_sub else 'no'
            print(f"{user.id:<4} | {user.plan:<6} | {user.subscription_status:<9} | {str(user.name):<18} | {user.email:<28} | {linked}")
        print("="*80 + "\n")

if __name__ == "__main__":
    view_users()
