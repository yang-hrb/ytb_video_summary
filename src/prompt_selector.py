import os
import csv
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PromptSelector:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.map_file = config_dir / "prompt_profile_map.csv"
        self.prompts_dir = config_dir / "prompt_types"
        
    def select_for_uploader(self, uploader: str) -> dict:
        """
        Select a prompt for the given uploader.
        """
        # Read map to find type
        prompt_type = "default"
        prompt_source = "default"
        
        if self.map_file.exists() and uploader:
            try:
                with open(self.map_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('uploader') == uploader:
                            ptype = row.get('prompt_type')
                            if ptype:
                                prompt_type = ptype
                                prompt_source = "csv"
                            break
            except Exception as e:
                logger.warning(f"Failed to read prompt_profile_map.csv: {e}")
                
        # Load from that type
        prompt_file = self.prompts_dir / f"{prompt_type}.txt"
        if not prompt_file.exists():
            if prompt_type != "default":
                logger.warning(f"Prompt type file missed: {prompt_file}, falling back to default.txt")
                prompt_type = "default"
                prompt_file = self.prompts_dir / f"{prompt_type}.txt"
                
        if not prompt_file.exists():
            return {
                "prompt_text": None,
                "prompt_type": prompt_type,
                "prompt_source": "builtin",
                "prompt_index": 0,
                "prompt_file": "builtin",
            }
            
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by '---'
            prompts = [p.strip() for p in content.split('\n---\n') if p.strip()]
            if not prompts:
                prompts = [p.strip() for p in content.split('---') if p.strip()]
            if not prompts:
                raise ValueError(f"Empty prompt file: {prompt_file}")
                
            index = random.randint(0, len(prompts) - 1)
            selected = prompts[index]
            
            return {
                "prompt_text": selected,
                "prompt_type": prompt_type,
                "prompt_source": prompt_source,
                "prompt_index": index,
                "prompt_file": prompt_file.name,
            }
        except Exception as e:
            logger.warning(f"Failed to read prompt file {prompt_file}: {e}")
            return {
                "prompt_text": None,
                "prompt_type": "error",
                "prompt_source": "builtin",
                "prompt_index": 0,
                "prompt_file": "builtin",
            }
