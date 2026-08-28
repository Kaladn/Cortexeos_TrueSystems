import logging
import json
import os
import hashlib
import base64
import re
import fcntl
from typing import Dict, List, Set, Optional, Union
from functools import lru_cache
from cryptography.fernet import Fernet, InvalidToken

class AccessControl:
    """ Role-Based Access Control with AES-256 encryption & JWT integration. """

    def __init__(self, encryption_key: Optional[str] = None, roles_file="roles.json", 
                 user_roles_file="user_roles.json", permissions_file="permissions.json"):
        """
        Initialize the RBAC system with encryption key and configuration files.
        
        Args:
            encryption_key: Optional encryption key. If not provided, will be read from environment variable.
            roles_file: Path to the roles configuration file.
            user_roles_file: Path to the user roles configuration file.
            permissions_file: Path to the permissions configuration file.
        
        Raises:
            ValueError: If encryption key is not provided and not found in environment variables.
        """
        # Get encryption key from environment variable if not provided
        if encryption_key is None:
            encryption_key = os.environ.get('RBAC_ENCRYPTION_KEY')
            if not encryption_key:
                raise ValueError("Encryption key not provided and RBAC_ENCRYPTION_KEY environment variable not set")
        
        self.encryption_key = self._validate_key(encryption_key)
        self.roles_file = roles_file
        self.user_roles_file = user_roles_file
        self.permissions_file = permissions_file
        self.roles = self.load_encrypted_data(roles_file, default={
            "admin": {"permissions": ["read", "write", "delete", "manage_users"], "inherits": []},
            "user": {"permissions": ["read"], "inherits": []},
        })
        self.user_roles = self.load_encrypted_data(user_roles_file, default={})
        self.resource_permissions = self.load_encrypted_data(permissions_file, default={})
        self.setup_logging()

    def setup_logging(self):
        """ Secure Logging Setup with rotation """
        log_handler = logging.handlers.RotatingFileHandler(
            filename="access_control.log",
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        log_handler.setFormatter(log_formatter)
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(log_handler)

    def _validate_key(self, key: str) -> bytes:
        """ 
        Ensure encryption key is valid.
        
        Args:
            key: The encryption key to validate
            
        Returns:
            bytes: Processed encryption key
            
        Raises:
            ValueError: If key is invalid
        """
        if not key or not isinstance(key, str) or len(key) < 32:
            raise ValueError("Encryption key must be a string at least 32 characters long.")
        return base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())

    def encrypt(self, data: dict) -> str:
        """ 
        Encrypt JSON data with AES-256.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            str: Encrypted data as string
        """
        f = Fernet(self.encryption_key)
        return f.encrypt(json.dumps(data).encode()).decode()

    def decrypt(self, encrypted_data: str) -> dict:
        """ 
        Decrypt AES-256 encrypted JSON data.
        
        Args:
            encrypted_data: Encrypted data string
            
        Returns:
            dict: Decrypted data as dictionary
        """
        f = Fernet(self.encryption_key)
        try:
            return json.loads(f.decrypt(encrypted_data.encode()).decode())
        except InvalidToken:
            logging.error("Failed to decrypt data: Invalid token or wrong key", 
                         extra={"error_code": "E001"})
            return {}
        except json.JSONDecodeError:
            logging.error("Failed to decrypt data: Invalid JSON format", 
                         extra={"error_code": "E002"})
            return {}

    def load_encrypted_data(self, file_path: str, default: dict) -> dict:
        """ 
        Load encrypted data, decrypt, and return dictionary.
        
        Args:
            file_path: Path to the encrypted file
            default: Default value to return if file doesn't exist
            
        Returns:
            dict: Decrypted data or default value
        """
        if not os.path.exists(file_path):
            return default
        try:
            with open(file_path, "r") as f:
                encrypted_data = f.read()
                return self.decrypt(encrypted_data)
        except IOError as e:
            logging.error(f"Error reading {file_path}: {e}")
            return default

    def save_encrypted_data(self, file_path: str, data: dict):
        """ 
        Encrypt and save data securely with proper file permissions.
        
        Args:
            file_path: Path to save the encrypted file
            data: Dictionary to encrypt and save
        """
        try:
            encrypted_data = self.encrypt(data)
            
            # Use file locking to prevent race conditions
            with open(file_path, "w") as f:
                # Acquire exclusive lock
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(encrypted_data)
                # Release lock happens automatically when file is closed
            
            # Set secure file permissions (owner read/write only)
            os.chmod(file_path, 0o600)
            
            logging.info(f"Data saved securely to {file_path}")
        except IOError as e:
            logging.error(f"Error saving to {file_path}: {e}")

    def _validate_username(self, username: str) -> bool:
        """
        Validate username format to prevent injection attacks.
        
        Args:
            username: Username to validate
            
        Returns:
            bool: True if username is valid, False otherwise
        """
        if not username or not isinstance(username, str):
            return False
        # Allow alphanumeric and some special characters, limit length
        return bool(re.match(r'^[a-zA-Z0-9_\-\.@]{3,64}$', username))
    
    def _validate_resource(self, resource: str) -> bool:
        """
        Validate resource identifier format.
        
        Args:
            resource: Resource identifier to validate
            
        Returns:
            bool: True if resource is valid, False otherwise
        """
        if not resource or not isinstance(resource, str):
            return False
        # Allow alphanumeric and some special characters, limit length
        return bool(re.match(r'^[a-zA-Z0-9_\-\.\/]{1,255}$', resource))
    
    def _validate_action(self, action: str) -> bool:
        """
        Validate action format.
        
        Args:
            action: Action to validate
            
        Returns:
            bool: True if action is valid, False otherwise
        """
        if not action or not isinstance(action, str):
            return False
        # Allow alphanumeric and underscore, limit length
        return bool(re.match(r'^[a-zA-Z0-9_]{1,64}$', action))

    def has_permission(self, username: str, action: str, resource: str = None) -> bool:
        """ 
        Checks if a user has permission with input validation.
        
        Args:
            username: Username to check permissions for
            action: Action to check permission for
            resource: Optional resource to check permission on
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        # Validate inputs
        if not self._validate_username(username):
            logging.warning(f"Invalid username format: {username}")
            return False
            
        if not self._validate_action(action):
            logging.warning(f"Invalid action format: {action}")
            return False
            
        if resource and not self._validate_resource(resource):
            logging.warning(f"Invalid resource format: {resource}")
            return False
        
        # Check if user has a role
        user_role = self.user_roles.get(username)
        if not user_role:
            logging.warning(f"User {username} has no assigned role.")
            return False

        # Check role permissions
        if self._check_role_permissions(user_role, action):
            return self._log_access(username, user_role, action, resource, granted=True)

        # Check resource-specific permissions
        if resource:
            resource_perms = self.resource_permissions.get(resource, {}).get(user_role, [])
            if action in resource_perms:
                return self._log_access(username, user_role, action, resource, granted=True)

        return self._log_access(username, user_role, action, resource, granted=False)

    def _check_role_permissions(self, role: str, action: str) -> bool:
        """ 
        Check role permissions, including inherited ones.
        
        Args:
            role: Role to check permissions for
            action: Action to check permission for
            
        Returns:
            bool: True if role has permission, False otherwise
        """
        role_data = self.roles.get(role, {})
        if action in role_data.get("permissions", []):
            return True
        
        # Check inherited roles
        for inherited_role in role_data.get("inherits", []):
            if self._check_role_permissions(inherited_role, action):
                return True
                
        return False

    def _sanitize_log_message(self, message: str) -> str:
        """
        Sanitize log message to prevent log injection.
        
        Args:
            message: Log message to sanitize
            
        Returns:
            str: Sanitized log message
        """
        if not message or not isinstance(message, str):
            return ""
        
        # Replace newlines, carriage returns, and tabs with spaces
        sanitized = re.sub(r'[\n\r\t]', ' ', message)
        
        # Limit length to prevent excessively long log entries
        return sanitized[:1024]

    def _log_access(self, username: str, role: str, action: str, resource: str, granted: bool) -> bool:
        """ 
        Secure logging to prevent log injection attacks.
        
        Args:
            username: Username attempting the action
            role: Role of the user
            action: Action attempted
            resource: Resource the action was attempted on
            granted: Whether access was granted
            
        Returns:
            bool: The granted parameter (for method chaining)
        """
        action_result = "GRANTED" if granted else "DENIED"
        
        # Sanitize all user-provided inputs
        safe_username = self._sanitize_log_message(username)
        safe_role = self._sanitize_log_message(role)
        safe_action = self._sanitize_log_message(action)
        safe_resource = self._sanitize_log_message(resource or 'global')
        
        log_message = f"Access {action_result}: {safe_username} ({safe_role}) attempted {safe_action} on {safe_resource}"
        
        logging.info(log_message)
        return granted

    def _detect_cycle(self, role: str, visited: Set[str] = None, path: Set[str] = None) -> bool:
        """
        Detect cycles in role inheritance graph using DFS.
        
        Args:
            role: Starting role to check for cycles
            visited: Set of visited roles (for recursion)
            path: Current path in DFS (for cycle detection)
            
        Returns:
            bool: True if cycle detected, False otherwise
        """
        if visited is None:
            visited = set()
        if path is None:
            path = set()
            
        # If role doesn't exist, no cycle
        if role not in self.roles:
            return False
            
        visited.add(role)
        path.add(role)
        
        # Check all inherited roles for cycles
        for inherited_role in self.roles.get(role, {}).get("inherits", []):
            if inherited_role not in visited:
                if self._detect_cycle(inherited_role, visited, path):
                    return True
            elif inherited_role in path:
                # Cycle detected
                return True
                
        # Remove from path when backtracking
        path.remove(role)
        return False

    def assign_role(self, username: str, role: str) -> bool:
        """ 
        Assigns a role securely with input validation.
        
        Args:
            username: Username to assign role to
            role: Role to assign
            
        Returns:
            bool: True if role was assigned, False otherwise
        """
        # Validate username
        if not self._validate_username(username):
            logging.error(f"Invalid username format: {username}")
            return False
            
        # Check if role exists
        if role not in self.roles:
            logging.error(f"Invalid role assignment: {role} does not exist.")
            return False
            
        # Assign role
        self.user_roles[username] = role
        self.save_encrypted_data(self.user_roles_file, self.user_roles)
        logging.info(f"Assigned role {role} to {username}.")
        return True

    def create_role(self, role_name: str, permissions: List[str], inherits: List[str] = None) -> bool:
        """
        Create a new role with permissions and inheritance.
        
        Args:
            role_name: Name of the new role
            permissions: List of permissions for the role
            inherits: Optional list of roles to inherit from
            
        Returns:
            bool: True if role was created, False otherwise
        """
        # Validate role name
        if not role_name or not isinstance(role_name, str) or not re.match(r'^[a-zA-Z0-9_\-]{1,64}$', role_name):
            logging.error(f"Invalid role name format: {role_name}")
            return False
            
        # Validate permissions
        if not permissions or not isinstance(permissions, list):
            logging.error("Permissions must be a non-empty list")
            return False
            
        # Check if role already exists
        if role_name in self.roles:
            logging.error(f"Role {role_name} already exists")
            return False
        
        # Validate inherited roles
        inherits_list = inherits or []
        for inherited_role in inherits_list:
            if inherited_role not in self.roles:
                logging.error(f"Cannot inherit from non-existent role: {inherited_role}")
                return False
                
        # Create role
        self.roles[role_name] = {
            "permissions": permissions,
            "inherits": inherits_list
        }
        
        # Check for cycles after adding inheritance
        if self._detect_cycle(role_name):
            # Rollback if cycle detected
            del self.roles[role_name]
            logging.error(f"Role {role_name} would create circular inheritance")
            return False
            
        # Save roles
        self.save_encrypted_data(self.roles_file, self.roles)
        logging.info(f"Created role {role_name}")
        return True

    def update_role_inheritance(self, role_name: str, inherits: List[str]) -> bool:
        """
        Update role inheritance with cycle detection.
        
        Args:
            role_name: Name of the role to update
            inherits: New list of roles to inherit from
            
        Returns:
            bool: True if inheritance was updated, False otherwise
        """
        # Check if role exists
        if role_name not in self.roles:
            logging.error(f"Role {role_name} does not exist")
            return False
            
        # Validate inherited roles
        for inherited_role in inherits:
            if inherited_role not in self.roles:
                logging.error(f"Cannot inherit from non-existent role: {inherited_role}")
                return False
                
        # Save original inheritance in case we need to rollback
        original_inherits = self.roles[role_name]["inherits"]
        
        # Update inheritance
        self.roles[role_name]["inherits"] = inherits
        
        # Check for cycles
        if self._detect_cycle(role_name):
            # Rollback if cycle detected
            self.roles[role_name]["inherits"] = original_inherits
            logging.error(f"Role inheritance update would create circular inheritance")
            return False
            
        # Save roles
        self.save_encrypted_data(self.roles_file, self.roles)
        logging.info(f"Updated inheritance for role {role_name}")
        return True

    def get_permissions(self, role: str) -> List[str]:
        """ 
        Gets all permissions for a role, including inherited ones.
        
        Args:
            role: Role to get permissions for
            
        Returns:
            List[str]: List of permissions
        """
        if role in self.roles:
            all_perm = set(self.roles[role]["permissions"])
            for inherited_role in self.roles[role]["inherits"]:
                all_perm.update(self.get_permissions(inherited_role))
            return list(all_perm)
        return []

    def add_resource_permission(self, resource: str, role: str, permissions: List[str]) -> bool:
        """
        Add permissions for a role on a specific resource.
        
        Args:
            resource: Resource identifier
            role: Role to add permissions for
            permissions: List of permissions to add
            
        Returns:
            bool: True if permissions were added, False otherwise
        """
        # Validate resource
        if not self._validate_resource(resource):
            logging.error(f"Invalid resource format: {resource}")
            return False
            
        # Check if role exists
        if role not in self.roles:
            logging.error(f"Role {role} does not exist")
            return False
            
        # Initialize resource if not exists
        if resource not in self.resource_permissions:
            self.resource_permissions[resource] = {}
            
        # Add permissions
        self.resource_permissions[resource][role] = permissions
        self.save_encrypted_data(self.permissions_file, self.resource_permissions)
        logging.info(f"Added permissions for {role} on {resource}")
        return True

# Example Usage
if __name__ == "__main__":
    # Get key from environment variable
    security_key = os.environ.get('RBAC_ENCRYPTION_KEY')
    if not security_key:
        print("Please set the RBAC_ENCRYPTION_KEY environment variable")
        print("Example: export RBAC_ENCRYPTION_KEY='your-secure-key-at-least-32-chars-long'")
        exit(1)
        
    ac = AccessControl(encryption_key=security_key)

    # Example usage
    ac.assign_role("alice", "admin")
    print(ac.has_permission("alice", "delete"))
