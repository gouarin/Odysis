from array import array

from traitlets import (
    Unicode, List, Instance, Float,
    Int, Bool, Union, Enum, observe
)
from traittypes import Array
from ipywidgets import (
    widget_serialization,
    DOMWidget, Widget, register,
    Color,
    Dropdown, FloatRangeSlider, FloatSlider, FloatText, Label,
    link,
    VBox, HBox
)

from .serialization import array_serialization
from .vtk_loader import (
    load_vtk, FLOAT32, UINT32,
    get_ugrid_vertices, get_ugrid_faces, get_ugrid_tetras, get_ugrid_data
)

odysis_version = '^0.1.0'


@register
class Component(Widget):
    """A data component widget."""
    # _view_name = Unicode('ComponentView').tag(sync=True)
    _model_name = Unicode('ComponentModel').tag(sync=True)
    _view_module = Unicode('odysis').tag(sync=True)
    _model_module = Unicode('odysis').tag(sync=True)
    _view_module_version = Unicode(odysis_version).tag(sync=True)
    _model_module_version = Unicode(odysis_version).tag(sync=True)

    name = Unicode().tag(sync=True)
    # TODO: validate data as being 1-D array, and validate dtype
    array = Array(default_value=array(FLOAT32)).tag(sync=True, **array_serialization)
    min = Float(allow_none=True, default_value=None).tag(sync=True)
    max = Float(allow_none=True, default_value=None).tag(sync=True)


@register
class Data(Widget):
    """A data widget."""
    # _view_name = Unicode('DataView').tag(sync=True)
    _model_name = Unicode('DataModel').tag(sync=True)
    _view_module = Unicode('odysis').tag(sync=True)
    _model_module = Unicode('odysis').tag(sync=True)
    _view_module_version = Unicode(odysis_version).tag(sync=True)
    _model_module_version = Unicode(odysis_version).tag(sync=True)

    name = Unicode().tag(sync=True)
    components = List(Instance(Component)).tag(sync=True, **widget_serialization)


class BlockType():
    pass


@register
class Block(Widget, BlockType):
    _view_name = Unicode('BlockView').tag(sync=True)
    _model_name = Unicode('BlockModel').tag(sync=True)
    _view_module = Unicode('odysis').tag(sync=True)
    _model_module = Unicode('odysis').tag(sync=True)
    _view_module_version = Unicode(odysis_version).tag(sync=True)
    _model_module_version = Unicode(odysis_version).tag(sync=True)

    _blocks = List(Instance(BlockType)).tag(sync=True, **widget_serialization)

    visible = Bool(True).tag(sync=True)
    colored = Bool(True).tag(sync=True)
    # TODO position, rotation, scale, wireframe
    colormap_min = Float().tag(sync=True)
    colormap_max = Float().tag(sync=True)
    visualized_data = Unicode().tag(sync=True)
    visualized_components = List(Union(trait_types=(Unicode(), Int()))).tag(sync=True)

    def apply(self, block):
        block._validate_parent(self)

        if block._parent_block is not None:
            raise RuntimeError('Cannot apply the same effect at different places')

        block._parent_block = self
        self._blocks = list([b for b in self._blocks] + [block])

    def remove(self, block):
        block._parent_block = None
        self._blocks = list([b for b in self._blocks if b.model_id != block.model_id])

    def _validate_parent(self, parent):
        pass

    def warp(self, *args, **kwargs):
        effect = Warp(*args, **kwargs)
        self.apply(effect)
        return effect

    def vector_field(self, *args, **kwargs):
        effect = VectorField(*args, **kwargs)
        self.apply(effect)
        return effect

    def points(self, *args, **kwargs):
        raise RuntimeError('Points effect not implemented yet')

    def clip(self, *args, **kwargs):
        effect = Clip(*args, **kwargs)
        self.apply(effect)
        return effect

    def slice(self, *args, **kwargs):
        raise RuntimeError('Slice effect not implemented yet')

    def threshold(self, *args, **kwargs):
        effect = Threshold(*args, **kwargs)
        self.apply(effect)
        return effect

    def iso_surface(self, *args, **kwargs):
        raise RuntimeError('IsoSurface effect not implemented yet')


def _grid_data_to_data_widget(grid_data):
    data = []
    for key, value in grid_data.items():
        d = Data(
            name=key,
            components=[
                Component(name=comp_name, array=comp['array'], min=comp['min'], max=comp['max'])
                for comp_name, comp in value.items()
            ]
        )
        data.append(d)

    return data


@register
class Mesh(Block):
    """A 3-D Mesh widget."""
    _view_name = Unicode('MeshView').tag(sync=True)
    _model_name = Unicode('MeshModel').tag(sync=True)
    _view_module = Unicode('odysis').tag(sync=True)
    _model_module = Unicode('odysis').tag(sync=True)
    _view_module_version = Unicode(odysis_version).tag(sync=True)
    _model_module_version = Unicode(odysis_version).tag(sync=True)

    # TODO: validate vertices/faces/tetras as being 1-D array, and validate dtype
    vertices = Array(default_value=array(FLOAT32)).tag(sync=True, **array_serialization)
    faces = Array(default_value=array(UINT32)).tag(sync=True, **array_serialization)
    tetras = Array(default_value=array(UINT32)).tag(sync=True, **array_serialization)
    data = List(Instance(Data), default_value=[]).tag(sync=True, **widget_serialization)
    bounding_box = List().tag(sync=True)

    @staticmethod
    def from_vtk(path):
        grid = load_vtk(path)

        grid.ComputeBounds()
        bounding_box = grid.GetBounds()

        return Mesh(
            vertices=get_ugrid_vertices(grid),
            faces=get_ugrid_faces(grid),
            tetras=get_ugrid_tetras(grid),
            data=_grid_data_to_data_widget(get_ugrid_data(grid)),
            bounding_box=bounding_box
        )

    def reload(self, path,
               reload_vertices=False, reload_faces=False,
               reload_data=True, reload_tetras=False):
        grid = load_vtk(path)

        if reload_vertices:
            self.vertices = get_ugrid_vertices(grid)
        if reload_faces:
            self.faces = get_ugrid_faces(grid)
        if reload_tetras:
            self.tetras = get_ugrid_tetras(grid)
        if reload_data:
            self.data = _grid_data_to_data_widget(get_ugrid_data(grid))


@register
class PluginBlock(Block):
    _view_name = Unicode('PluginBlockView').tag(sync=True)
    _model_name = Unicode('PluginBlockModel').tag(sync=True)

    _parent_block = Instance(BlockType, allow_none=True, default_value=None)

    _available_input_data = List([])
    _available_input_components = List([])
    _input_data_dim = Int(3)

    # TODO Validate data/components names and synchronise JavaScript -> Python
    input_data = Unicode(allow_none=True, default_value=None).tag(sync=True)
    input_components = List(Union((Unicode(), Int()))).tag(sync=True)

    def _get_data(self, parent):
        block = parent
        while not isinstance(block, Mesh):
            block = block._parent_block
        return block.data

    @observe('_parent_block')
    def _update_parent(self, change):
        parent = change['new']
        if parent is None:
            return

        data = self._get_data(parent)

        self._available_input_data = [d.name for d in data]
        self.input_data = self._available_input_data[0]

    @observe('input_data')
    def _update_available_components(self, change):
        data = self._get_data(self._parent_block)
        for d in data:
            if d.name == change['new']:
                current_data = d
        self._available_input_components = [c.name for c in current_data.components] + [0]

    @observe('_available_input_components')
    def _update_input_components(self, change):
        available_components = change['new']

        # Check current components validity
        components_are_valid = True
        if not len(self.input_components):
            components_are_valid = False
        for c in self.input_components:
            if c not in available_components:
                components_are_valid = False
        if components_are_valid:
            return

        new_components = []
        for dim in range(self._input_data_dim):
            if len(available_components) <= dim:
                new_components.append(0)
                continue
            new_components.append(available_components[dim])

        self.input_components = new_components

    def _link_dropdown(self, dropdown, dim):
        def handle_dropdown_change(change):
            copy = self.input_components.copy()
            copy[dim] = change['new']
            self.input_components = copy
        dropdown.observe(handle_dropdown_change, names=['value'])

        def handle_input_change(change):
            dropdown.value = self.input_components[dim]
        self.observe(handle_input_change, names=['input_components'])

        link((dropdown, 'options'), (self, '_available_input_components'))

    def interact(self):
        component_dropdowns = [Label(value="Input components:")]
        for dim in range(self._input_data_dim):
            dropdown = Dropdown(
                options=self._available_input_components,
                value=self.input_components[dim]
            )
            dropdown.layout.width = 'fit-content'
            self._link_dropdown(dropdown, dim)
            component_dropdowns.append(dropdown)

        data_dropdown = Dropdown(
            options=self._available_input_data,
            value=self.input_data
        )
        data_dropdown.layout.width = 'fit-content'
        link((data_dropdown, 'value'), (self, 'input_data'))

        return VBox((
            HBox((Label(value='Input data:'), data_dropdown)),
            HBox(component_dropdowns)
        ))


@register
class Warp(PluginBlock):
    _view_name = Unicode('WarpView').tag(sync=True)
    _model_name = Unicode('WarpModel').tag(sync=True)

    _input_data_dim = Int(3)

    factor = Float(0.0).tag(sync=True)
    factor_min = Float(-10.0)
    factor_max = Float(10.0)

    def interact(self):
        # TODO Update the step of the slider
        slider = FloatSlider(
            description='Warp factor',
            min=self.factor_min,
            max=self.factor_max,
            value=0.0
        )
        slider_min = FloatText(description='Factor Min', value=self.factor_min)
        slider_max = FloatText(description='Factor Max', value=self.factor_max)
        link((self, 'factor'), (slider, 'value'))
        link((self, 'factor_min'), (slider, 'min'))
        link((self, 'factor_min'), (slider_min, 'value'))
        link((self, 'factor_max'), (slider, 'max'))
        link((self, 'factor_max'), (slider_max, 'value'))

        input_dim_widget = super(Warp, self).interact()

        return HBox((
            input_dim_widget,
            VBox((slider, slider_min, slider_max))
        ))


@register
class Clip(PluginBlock):
    _view_name = Unicode('ClipView').tag(sync=True)
    _model_name = Unicode('ClipModel').tag(sync=True)

    plane_position = Float(0.0).tag(sync=True)
    plane_position_min = Float(-10)
    plane_position_max = Float(10)
    plane_normal = List(Float()).tag(sync=True)

    def interact(self):
        # TODO Update the step of the slider
        slider = FloatSlider(
            description='Plane position',
            min=self.plane_position_min,
            max=self.plane_position_max,
            value=0.0
        )
        slider_min = FloatText(description='Min', value=self.plane_position_min)
        slider_max = FloatText(description='Max', value=self.plane_position_max)
        link((self, 'plane_position'), (slider, 'value'))
        link((self, 'plane_position_min'), (slider, 'min'))
        link((self, 'plane_position_min'), (slider_min, 'value'))
        link((self, 'plane_position_max'), (slider, 'max'))
        link((self, 'plane_position_max'), (slider_max, 'value'))
        return VBox((slider, slider_min, slider_max))

    def _validate_parent(self, parent):
        block = parent
        while not isinstance(block, Mesh):
            if isinstance(block, Warp):
                raise RuntimeError('Cannot apply a Clip after a Warp effect')
            block = block._parent_block


@register
class VectorField(PluginBlock):
    _view_name = Unicode('VectorFieldView').tag(sync=True)
    _model_name = Unicode('VectorFieldModel').tag(sync=True)

    _input_data_dim = Int(3)

    length_factor = Float(1.).tag(sync=True)
    width = Int(1).tag(sync=True)
    percentage_vectors = Float(1.).tag(sync=True)
    distribution = Enum(('ordered', 'random'), default_value='ordered').tag(sync=True)
    mode = Enum(('volume', 'surface'), default_value='volume').tag(sync=True)

    def _validate_parent(self, parent):
        block = parent
        while not isinstance(block, Mesh):
            if isinstance(block, VectorField):
                raise RuntimeError('Cannot apply a VectorField after a VectorField effect')
            block = block._parent_block


@register
class Threshold(PluginBlock):
    _view_name = Unicode('ThresholdView').tag(sync=True)
    _model_name = Unicode('ThresholdModel').tag(sync=True)

    _input_data_dim = Int(1)

    lower_bound = Float().tag(sync=True)
    upper_bound = Float().tag(sync=True)

    def interact(self):
        slider = FloatRangeSlider(
            description='Bounds',
            min=self.lower_bound,
            max=self.upper_bound,
            value=[self.lower_bound, self.upper_bound]
        )
        slider.observe(self._on_slider_change, 'value')

        input_dim_widget = super(Threshold, self).interact()

        return HBox((
            input_dim_widget,
            VBox((slider, ))
        ))

    def _on_slider_change(self, change):
        self.lower_bound = change['new'][0]
        self.upper_bound = change['new'][1]


@register
class Scene(DOMWidget):
    """A 3-D Scene widget."""
    _view_name = Unicode('SceneView').tag(sync=True)
    _model_name = Unicode('SceneModel').tag(sync=True)
    _view_module = Unicode('odysis').tag(sync=True)
    _model_module = Unicode('odysis').tag(sync=True)
    _view_module_version = Unicode(odysis_version).tag(sync=True)
    _model_module_version = Unicode(odysis_version).tag(sync=True)

    mesh = Instance(Mesh).tag(sync=True, **widget_serialization)

    background_color = Color('#fff').tag(sync=True)
