from main import app, db, User

def view_users():
    with app.app_context():
        users = User.query.all()
        if not users:
            print("\nNo users found in the database yet.")
            return
        
        print("\n" + "="*80)
        print(f"{'ID':<4} | {'Name':<20} | {'Email':<30} | {'Last Login'}")
        print("-" * 80)
        for user in users:
            login_str = user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else "N/A"
            print(f"{user.id:<4} | {str(user.name):<20} | {user.email:<30} | {login_str}")
        print("="*80 + "\n")

if __name__ == "__main__":
    view_users()
