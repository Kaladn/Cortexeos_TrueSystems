import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from truecore.app import app
from truecore.core.db import db
from truecore.core.models import Role, User


def main() -> None:
    username = os.getenv("TRUECORE_ADMIN_USER", "admin")
    password = os.getenv("TRUECORE_ADMIN_PASS", "change-this-now")
    reset_password = os.getenv("TRUECORE_ADMIN_RESET", "false").lower() == "true"

    with app.app_context():
        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.session.add(admin_role)
            db.session.commit()

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, role_id=admin_role.id)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Created admin user: {username}")
        elif reset_password:
            user.set_password(password)
            user.role_id = admin_role.id
            db.session.commit()
            print(f"Reset admin user: {username}")
        else:
            print(f"Admin user already exists: {username}")


if __name__ == "__main__":
    main()
