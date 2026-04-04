from main import app, db, User

def view_users():
    with app.app_context():
        users = User.query.all()
        if not users:
            print("\nNo users found in the database yet.")
            return
        
        print("\n" + "="*80)
        print(f"{'ID':<4} | {'Name':<30} | {'Email'}")
        print("-" * 80)
        for user in users:
            print(f"{user.id:<4} | {str(user.name):<30} | {user.email}")
        print("="*80 + "\n")

if __name__ == "__main__":
    view_users()
