import json
import os
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

AUTH_FILE = "auth_data.json"
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk_str() -> str:
    return datetime.now(MSK_TZ).strftime("%Y-%m-%d %H:%M:%S")

class AuthManager:
    def __init__(self, filepath: str = AUTH_FILE, admin_ids: Optional[List[int]] = None):
        self.filepath = filepath
        self.admin_ids = set(admin_ids or [78429883])
        self.data = self._load()
        # Гарантируем, что админы всегда в списке авторизованных
        for aid in self.admin_ids:
            if str(aid) not in self.data["users"]:
                self.data["users"][str(aid)] = {
                    "user_id": aid,
                    "username": "Admin",
                    "full_name": "Главный Администратор",
                    "added_at": get_now_msk_str(),
                    "role": "admin"
                }
        self._save()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "users": {},
            "invites": {}
        }

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    def is_authorized(self, user_id: int) -> bool:
        return str(user_id) in self.data["users"] or user_id in self.admin_ids

    def get_all_authorized_users(self) -> Dict[str, Any]:
        return self.data.get("users", {})

    def get_authorized_chat_ids(self) -> List[int]:
        return [int(uid) for uid in self.data.get("users", {}).keys()]

    def generate_invite_token(self, created_by: int) -> str:
        """Генерация одноразового 6-значного буквенно-цифрового пароля"""
        chars = string.ascii_uppercase + string.digits
        # Исключаем похожие символы (0, O, 1, I) для удобства ввода
        clean_chars = [c for c in chars if c not in "0OI1"]
        token = "".join(random.choices(clean_chars, k=6))
        
        self.data["invites"][token] = {
            "token": token,
            "created_by": created_by,
            "created_at": get_now_msk_str(),
            "used": False,
            "used_by": None,
            "used_at": None
        }
        self._save()
        return token

    def use_invite_token(self, token: str, user_id: int, username: str, full_name: str) -> bool:
        """Попытка активации одноразового пароля"""
        token = token.strip().upper()
        if token in self.data["invites"] and not self.data["invites"][token]["used"]:
            # Помечаем как использованный
            self.data["invites"][token]["used"] = True
            self.data["invites"][token]["used_by"] = user_id
            self.data["invites"][token]["used_at"] = get_now_msk_str()

            # Добавляем пользователя
            self.data["users"][str(user_id)] = {
                "user_id": user_id,
                "username": username or "",
                "full_name": full_name or "Сотрудник",
                "added_at": get_now_msk_str(),
                "added_via_token": token,
                "role": "user"
            }
            self._save()
            return True
        return False

    def revoke_user_access(self, user_id: int) -> bool:
        """Отозвать доступ у пользователя (кроме админа)"""
        if user_id in self.admin_ids:
            return False
        uid_str = str(user_id)
        if uid_str in self.data["users"]:
            del self.data["users"][uid_str]
            self._save()
            return True
        return False

    def get_active_invites(self) -> List[Dict[str, Any]]:
        """Список неиспользованных инвайт-паролей"""
        return [inv for inv in self.data.get("invites", {}).values() if not inv.get("used")]

    def revoke_invite(self, token: str) -> bool:
        """Аннулировать инвайт-код"""
        token = token.strip().upper()
        if token in self.data["invites"]:
            del self.data["invites"][token]
            self._save()
            return True
        return False

auth_manager = AuthManager()
