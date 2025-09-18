"""Prompt manager for flexible memory synthesis"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class PromptManager:
    """Manage user-defined prompts for memory synthesis"""
    
    def __init__(self, memory_home: Optional[str] = None):
        """Initialize prompt manager"""
        if memory_home is None:
            memory_home = os.path.expanduser(os.getenv("MEMORY_HOME", "~/.memory"))
        
        self.prompts_dir = Path(memory_home) / "prompts"
        self.custom_dir = self.prompts_dir / "custom"
        self.default_file = self.prompts_dir / "default.yaml"
        self.active_profile_file = self.prompts_dir / "active_profile.txt"
        
        # Create directories if they don't exist
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.custom_dir.mkdir(exist_ok=True)
        
        # Initialize default prompts if not present
        if not self.default_file.exists():
            self._create_default_prompts()
        
        # Load active profile
        self.active_profile = self._load_active_profile()
    
    def _create_default_prompts(self):
        """Create default prompt templates"""
        from .templates import DefaultPromptTemplates
        
        defaults = {
            'daily': DefaultPromptTemplates.DAILY_DEFAULT,
            'weekly': DefaultPromptTemplates.WEEKLY_DEFAULT,
            'monthly': DefaultPromptTemplates.MONTHLY_DEFAULT,
            'contextual': DefaultPromptTemplates.CONTEXTUAL_TEMPLATES
        }
        
        with open(self.default_file, 'w') as f:
            yaml.dump(defaults, f, default_flow_style=False, sort_keys=False)
        
        print(f"✓ Created default prompts at {self.default_file}")
    
    def _load_active_profile(self) -> str:
        """Load the active profile name"""
        if self.active_profile_file.exists():
            return self.active_profile_file.read_text().strip()
        return "default"
    
    def set_active_profile(self, profile_name: str) -> bool:
        """Set the active profile"""
        if profile_name == "default" or (self.custom_dir / f"{profile_name}.yaml").exists():
            self.active_profile_file.write_text(profile_name)
            self.active_profile = profile_name
            print(f"✓ Active profile set to: {profile_name}")
            return True
        else:
            print(f"✗ Profile '{profile_name}' not found")
            return False
    
    def get_prompt(self, 
                   prompt_type: str, 
                   profile: Optional[str] = None,
                   context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a prompt for the specified type
        
        Args:
            prompt_type: 'daily', 'weekly', 'monthly', or 'contextual'
            profile: Profile name to use (defaults to active profile)
            context: Context data for dynamic prompt selection
        
        Returns:
            The prompt template string
        """
        profile = profile or self.active_profile
        
        # Load the appropriate prompt file
        if profile == "default":
            prompts = self._load_prompts_file(self.default_file)
        else:
            custom_file = self.custom_dir / f"{profile}.yaml"
            if custom_file.exists():
                prompts = self._load_prompts_file(custom_file)
            else:
                print(f"Profile '{profile}' not found, using default")
                prompts = self._load_prompts_file(self.default_file)
        
        # Handle contextual prompts
        if prompt_type == 'contextual' and context:
            contextual_prompt = self._select_contextual_prompt(prompts, context)
            if contextual_prompt:
                return contextual_prompt
            # Fall back to daily if no contextual match
            prompt_type = 'daily'
        
        # Return the requested prompt type
        return prompts.get(prompt_type, prompts.get('daily', ''))
    
    def _load_prompts_file(self, file_path: Path) -> Dict[str, Any]:
        """Load prompts from a YAML file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading prompts from {file_path}: {e}")
            return {}
    
    def _select_contextual_prompt(self, 
                                  prompts: Dict[str, Any], 
                                  context: Dict[str, Any]) -> Optional[str]:
        """Select a contextual prompt based on the context data"""
        contextual = prompts.get('contextual', {})
        
        if not isinstance(contextual, list):
            contextual = [contextual] if contextual else []
        
        for rule in contextual:
            if isinstance(rule, dict) and 'when' in rule and 'prompt' in rule:
                if self._evaluate_condition(rule['when'], context):
                    return self._interpolate_prompt(rule['prompt'], context)
        
        return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition against the context"""
        # Simple condition evaluation
        # Examples: "stress_level > 5", "task_count > 10", "has_deadlines"
        
        if '>' in condition:
            key, value = condition.split('>')
            key = key.strip()
            value = float(value.strip())
            return context.get(key, 0) > value
        elif '<' in condition:
            key, value = condition.split('<')
            key = key.strip()
            value = float(value.strip())
            return context.get(key, 0) < value
        elif '==' in condition:
            key, value = condition.split('==')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            return str(context.get(key, '')) == value
        else:
            # Simple boolean check
            return bool(context.get(condition, False))
    
    def _interpolate_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Replace template variables in prompt with context values"""
        # Replace {{variable}} with context values
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))
        
        return re.sub(r'\{\{(\w+)\}\}', replace_var, prompt)
    
    def save_prompt(self, 
                   profile_name: str,
                   prompt_type: str,
                   prompt_content: str) -> bool:
        """Save a prompt to a profile"""
        if profile_name == "default":
            file_path = self.default_file
        else:
            file_path = self.custom_dir / f"{profile_name}.yaml"
        
        # Load existing prompts
        if file_path.exists():
            prompts = self._load_prompts_file(file_path)
        else:
            prompts = {}
        
        # Update the prompt
        prompts[prompt_type] = prompt_content
        
        # Save back to file
        try:
            with open(file_path, 'w') as f:
                yaml.dump(prompts, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Saved {prompt_type} prompt to {profile_name}")
            return True
        except Exception as e:
            print(f"Error saving prompt: {e}")
            return False
    
    def list_profiles(self) -> List[str]:
        """List all available prompt profiles"""
        profiles = ["default"]
        
        # Add custom profiles
        for file in self.custom_dir.glob("*.yaml"):
            profiles.append(file.stem)
        
        return profiles
    
    def create_profile(self, profile_name: str, base_profile: str = "default") -> bool:
        """Create a new profile based on an existing one"""
        if profile_name == "default":
            print("Cannot create a profile named 'default'")
            return False
        
        new_file = self.custom_dir / f"{profile_name}.yaml"
        if new_file.exists():
            print(f"Profile '{profile_name}' already exists")
            return False
        
        # Copy from base profile
        if base_profile == "default":
            base_file = self.default_file
        else:
            base_file = self.custom_dir / f"{base_profile}.yaml"
        
        if not base_file.exists():
            print(f"Base profile '{base_profile}' not found")
            return False
        
        # Copy the prompts
        prompts = self._load_prompts_file(base_file)
        
        try:
            with open(new_file, 'w') as f:
                yaml.dump(prompts, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Created profile '{profile_name}' based on '{base_profile}'")
            return True
        except Exception as e:
            print(f"Error creating profile: {e}")
            return False
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a custom profile"""
        if profile_name == "default":
            print("Cannot delete the default profile")
            return False
        
        profile_file = self.custom_dir / f"{profile_name}.yaml"
        if not profile_file.exists():
            print(f"Profile '{profile_name}' not found")
            return False
        
        try:
            profile_file.unlink()
            
            # If this was the active profile, switch to default
            if self.active_profile == profile_name:
                self.set_active_profile("default")
            
            print(f"✓ Deleted profile '{profile_name}'")
            return True
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False
    
    def get_profile_prompts(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """Get all prompts for a profile"""
        profile_name = profile_name or self.active_profile
        
        if profile_name == "default":
            file_path = self.default_file
        else:
            file_path = self.custom_dir / f"{profile_name}.yaml"
        
        if not file_path.exists():
            print(f"Profile '{profile_name}' not found")
            return {}
        
        return self._load_prompts_file(file_path)