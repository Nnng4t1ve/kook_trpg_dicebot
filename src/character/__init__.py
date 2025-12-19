"""角色卡模块"""
from .models import Character
from .manager import CharacterManager
from .importer import CharacterImporter
from .npc import NPCManager, NPC_TEMPLATES, generate_npc_from_template

__all__ = ["Character", "CharacterManager", "CharacterImporter", "NPCManager", "NPC_TEMPLATES", "generate_npc_from_template"]
