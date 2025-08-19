from typing import Dict, Any, List, Optional, ClassVar
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QObject, pyqtSignal

from services.tag_service import tag_service

@dataclass
class StyleCondition:
    """Defines when a style should be active based on tag values"""
    tag_path: str = ""  # Full tag path in form "[db_name]::tag_name"
    operator: str = "=="  # ==, !=, >, <, >=, <=, between, outside
    value: Any = None
    value2: Any = None  # For range operators
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StyleCondition':
        return cls(**data)

@dataclass
class ConditionalStyle:
    """A style that can be conditionally applied based on tag values"""
    name: str = ""
    style_id: str = ""
    conditions: List[StyleCondition] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""
    hover_properties: Dict[str, Any] = field(default_factory=dict)
    click_properties: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationProperties = field(default_factory=AnimationProperties)
    priority: int = 0  # Higher priority wins when multiple conditions match
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'style_id': self.style_id,
            'conditions': [cond.to_dict() for cond in self.conditions],
            'properties': self.properties,
            'tooltip': self.tooltip,
            'hover_properties': self.hover_properties,
            'click_properties': self.click_properties,
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
            tooltip=data.get('tooltip', ''),
            hover_properties=data.get('hover_properties', {}),
            click_properties=data.get('click_properties', {}),
            priority=data.get('priority', 0)
        )
        if 'animation' in data:
            style.animation = AnimationProperties.from_dict(data['animation'])
        return style

@dataclass
class ConditionalStyleManager(QObject):
    """Manages conditional styles for buttons"""
    styles_changed: ClassVar[pyqtSignal] = pyqtSignal()
    parent: Optional[QObject] = None
    conditional_styles: List[ConditionalStyle] = field(default_factory=list)
    default_style: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.parent)
    
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
    
    def get_active_style(self, tag_values: Optional[Dict[str, Any]] = None, state: Optional[str] = None) -> Dict[str, Any]:
        """Determine which style should be active based on tag values.

        Parameters
        ----------
        tag_values: Dict[str, Any], optional
            Current tag values; if not provided, values will be resolved via ``tag_service``.
        state: Optional[str]
            Optional state for which to retrieve additional properties.
            Supported states: ``"hover"`` and ``"click"``.
        """
        tag_values = tag_values or {}
        matching_styles = []

        for style in self.conditional_styles:
            if self._evaluate_conditions(style.conditions, tag_values):
                matching_styles.append(style)
        
        if matching_styles:
            # Return the highest priority style
            best_style = max(matching_styles, key=lambda s: s.priority)
            props = dict(best_style.properties)
            if state == 'hover':
                props.update(best_style.hover_properties)
            elif state == 'click':
                props.update(best_style.click_properties)
            if best_style.tooltip:
                props['tooltip'] = best_style.tooltip
            return props

        return dict(self.default_style)
    
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
            tag_value = tag_service.get_tag_value(condition.tag_path)
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
