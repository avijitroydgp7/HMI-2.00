from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

@dataclass
class StyleCondition:
    """Defines when a style should be active based on tag values"""
    tag_path: str = ""
    operator: str = "=="  # ==, !=, >, <, >=, <=, between, outside
    value: Any = None
    value2: Any = None  # For range operators
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StyleCondition':
        return cls(**data)

@dataclass
class AnimationProperties:
    """Animation settings for button styles"""
    enabled: bool = False
    type: str = "pulse"  # pulse, color_shift, scale, glow
    duration: int = 1000  # milliseconds
    intensity: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnimationProperties':
        return cls(**data)

@dataclass
class ConditionalStyle:
    """A style that can be conditionally applied based on tag values"""
    name: str = ""
    style_id: str = ""
    conditions: List[StyleCondition] = None
    properties: Dict[str, Any] = None
    animation: AnimationProperties = None
    priority: int = 0  # Higher priority wins when multiple conditions match
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.properties is None:
            self.properties = {}
        if self.animation is None:
            self.animation = AnimationProperties()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'style_id': self.style_id,
            'conditions': [cond.to_dict() for cond in self.conditions],
            'properties': self.properties,
            'animation': self.animation.to_dict(),
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalStyle':
        style = cls(
            name=data.get('name', ''),
            style_id=data.get('style_id', ''),
            conditions=[StyleCondition.from_dict(cond) for cond in data.get('conditions', [])],
            properties=data.get('properties', {}),
            priority=data.get('priority', 0)
        )
        if 'animation' in data:
            style.animation = AnimationProperties.from_dict(data['animation'])
        return style

class ConditionalStyleManager(QObject):
    """Manages conditional styles for buttons"""
    styles_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conditional_styles: List[ConditionalStyle] = []
        self.default_style: Dict[str, Any] = {}
    
    def add_style(self, style: ConditionalStyle):
        """Add a new conditional style"""
        self.conditional_styles.append(style)
        self.styles_changed.emit()
    
    def remove_style(self, index: int):
        """Remove a conditional style by index"""
        if 0 <= index < len(self.conditional_styles):
            del self.conditional_styles[index]
            self.styles_changed.emit()
    
    def update_style(self, index: int, style: ConditionalStyle):
        """Update an existing conditional style"""
        if 0 <= index < len(self.conditional_styles):
            self.conditional_styles[index] = style
            self.styles_changed.emit()
    
    def get_active_style(self, tag_values: Dict[str, Any]) -> Dict[str, Any]:
        """Determine which style should be active based on tag values"""
        matching_styles = []
        
        for style in self.conditional_styles:
            if self._evaluate_conditions(style.conditions, tag_values):
                matching_styles.append(style)
        
        if matching_styles:
            # Return the highest priority style
            best_style = max(matching_styles, key=lambda s: s.priority)
            return best_style.properties
        
        return self.default_style
    
    def _evaluate_conditions(self, conditions: List[StyleCondition], tag_values: Dict[str, Any]) -> bool:
        """Evaluate if all conditions are met"""
        if not conditions:
            return True
        
        for condition in conditions:
            if not self._evaluate_single_condition(condition, tag_values):
                return False
        
        return True
    
    def _evaluate_single_condition(self, condition: StyleCondition, tag_values: Dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        tag_value = tag_values.get(condition.tag_path)
        if tag_value is None:
            return False
        
        try:
            if condition.operator == "==":
                return tag_value == condition.value
            elif condition.operator == "!=":
                return tag_value != condition.value
            elif condition.operator == ">":
                return float(tag_value) > float(condition.value)
            elif condition.operator == "<":
                return float(tag_value) < float(condition.value)
            elif condition.operator == ">=":
                return float(tag_value) >= float(condition.value)
            elif condition.operator == "<=":
                return float(tag_value) <= float(condition.value)
            elif condition.operator == "between":
                return float(condition.value) <= float(tag_value) <= float(condition.value2)
            elif condition.operator == "outside":
                return float(tag_value) < float(condition.value) or float(tag_value) > float(condition.value2)
        except (ValueError, TypeError):
            return False
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'conditional_styles': [style.to_dict() for style in self.conditional_styles],
            'default_style': self.default_style
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalStyleManager':
        """Deserialize from dictionary"""
        manager = cls()
        manager.conditional_styles = [
            ConditionalStyle.from_dict(style_data) 
            for style_data in data.get('conditional_styles', [])
        ]
        manager.default_style = data.get('default_style', {})
        return manager
