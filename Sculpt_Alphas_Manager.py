# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENCE BLOCK #####

bl_info = {
    "name": "Sculpt Alphas Manager",
    "description": "Displays thumbnails of alpha textures (by categories) for quicker assignment to sculpt brushes",
    "author": "Ryxx",
    "blender": (2, 81, 0),
    "version": (1, 0),
    "location": "Sculpt Mode > Properties Editor > Active Tool tab > Texture Panel",
    "category": "Sculpting"
}

import os
import sys
import bpy
import bpy.utils.previews
from bpy.types import Operator, Menu, Panel, PropertyGroup, AddonPreferences, Scene, WindowManager, BlendData
from bpy.props import StringProperty, EnumProperty

#--------------------------------------------------------------------------------------
# A D D O N   P R E F E R E N C E S
#--------------------------------------------------------------------------------------

class SculptAlphasManagerPreferences(AddonPreferences):

    bl_idname = __name__

    sculpt_alphas_library: StringProperty(
        name="",
        subtype='FILE_PATH',
        description = 'Main Folder containing the alphas textures used for sculpt brushes'
    )
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="FOLDERS SETUP INSTRUCTIONS:")
        col.label(text="Step 1 - Create a main folder that will contain your alpha textures collections and copy paste its location in the 'Library Path' field below.")
        col.label(text="Step 2 - In that main folder, create as many sub-folders as needed and name them as you wish. These will be displayed as Categories.")
        col.label(text="Step 3 - Fill each sub-folder with your own black and white alpha textures (formats accepted: jpeg, png, tiff). These will be displayed as thumbnails.")
        col = layout.column(align=True)
        col.label(text="LIBRARY PATH:")
        col.prop(self, "sculpt_alphas_library")

#--------------------------------------------------------------------------------------
# F U N C T I O N A L I T I E S
#--------------------------------------------------------------------------------------

# CATEGORIES PREVIEWS FUNCTION
def preview_sub_folders_categories(self, context):
    lib_path = context.preferences.addons[__name__].preferences.sculpt_alphas_library
        
    list_of_category_folders = []
    for folder in os.listdir(lib_path):
        if os.path.isdir(os.path.join(lib_path, folder)):
            list_of_category_folders.append(folder)

    return [(name, name, "") for name in list_of_category_folders]

# CATEGORY ITEMS PREVIEWS FUNCTION
def preview_items_in_folders(self, context):
    enum_items = []

    if context is None:
        return enum_items

    wm = context.window_manager
    lib_path = context.preferences.addons[__name__].preferences.sculpt_alphas_library
    selected_category_name = bpy.data.scenes["Scene"].category_pointer_prop.Categories
    directory = os.path.join(lib_path, selected_category_name)

    pcoll = preview_collections["main"]

    if directory == pcoll.my_previews_dir:
        return pcoll.my_previews

    if directory and os.path.exists(directory):
        image_paths = []
        for fn in os.listdir(directory):
            if fn.lower().endswith(".jpeg") or fn.lower().endswith(".jpg") or fn.lower().endswith(".png") or fn.lower().endswith(".tif"):
                image_paths.append(fn)

        for i, name in enumerate(image_paths):
            filepath = os.path.join(directory, name)
            icon = pcoll.get(name)
            if not icon:
                thumb = pcoll.load(name, filepath, 'IMAGE')
            else:
                thumb = pcoll[name]
            enum_items.append((name, name, "", thumb.icon_id, i))

    pcoll.my_previews = enum_items
    pcoll.my_previews_dir = directory
    return pcoll.my_previews

# OPEN CATEGORY FOLDER
class OpenCategoryFolder(bpy.types.Operator):
    bl_idname = "open.category_folder"
    bl_label = "Open Category Folder"
    bl_description = "Open selected category's folder in Windows explorer"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        lib_path = context.preferences.addons[__name__].preferences.sculpt_alphas_library
        selected_category_name = bpy.data.scenes["Scene"].category_pointer_prop.Categories
        
        if sys.platform == "win32":
            os.startfile(os.path.join(lib_path, selected_category_name))
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, os.path.join(lib_path, selected_category_name)])
        
        return {'FINISHED'}

# ASSIGN SELECTED ALPHA TO SCULPT BRUSH
class AssignAlphaToBrush(bpy.types.Operator):
    bl_idname = "texture.assign_alpha_to_brush"
    bl_label = "Assign Selected Alpha to Sculpt Brush"
    bl_description = "Assign the selected alpha texture to the sculpt brush"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        lib_path = context.preferences.addons[__name__].preferences.sculpt_alphas_library
        selected_category_name = bpy.data.scenes["Scene"].category_pointer_prop.Categories
        selected_alpha = bpy.context.window_manager.items_in_folders
        texname_no_extension = os.path.splitext(selected_alpha)[0]

        if bpy.context.tool_settings.sculpt.brush.texture is not None:
            sculpt_tex = bpy.context.tool_settings.sculpt.brush.texture
            bpy.data.textures.remove(sculpt_tex, do_unlink=True, do_id_user=True, do_ui_user=True)

        bpy.ops.image.open(filepath = os.path.join(lib_path, selected_category_name, selected_alpha))
        image_to_texture = bpy.data.textures.new(texname_no_extension, 'IMAGE')
        image_to_texture.image = bpy.data.images[selected_alpha]
        
        bpy.context.tool_settings.sculpt.brush.texture = bpy.data.textures[texname_no_extension]

        return {'FINISHED'}

# CATEGORY PROPERTY SCENE
class CategoryPropertyScene(bpy.types.PropertyGroup):
    
    Categories: EnumProperty(items = preview_sub_folders_categories)
    WindowManager.items_in_folders = EnumProperty(items=preview_items_in_folders)

#--------------------------------------------------------------------------------------
# T E X T U R E   P A N E L   E X T E N S I O N
#--------------------------------------------------------------------------------------

def sculpt_alphas_categories_prepend(self, context):
    layout = self.layout
    
    row = layout.row(align=True)
    row.prop(context.scene.category_pointer_prop, "Categories", text = '')
    row.operator("open.category_folder", text = "", icon ="FILE_FOLDER")
    col = layout.column(align=True)
    col.template_icon_view(context.window_manager, "items_in_folders", show_labels = True)
    col.operator("texture.assign_alpha_to_brush", text = "Assign Alpha to Brush", icon ="BRUSH_DATA")

#--------------------------------------------------------------------------------------
# R E G I S T R Y
#--------------------------------------------------------------------------------------

classes = (
    SculptAlphasManagerPreferences,
    OpenCategoryFolder,
    AssignAlphaToBrush,
    CategoryPropertyScene
)

preview_collections = {}

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    bpy.types.VIEW3D_PT_tools_brush_texture.prepend(sculpt_alphas_categories_prepend)

    Scene.category_pointer_prop = bpy.props.PointerProperty(type = CategoryPropertyScene)

    pcoll = bpy.utils.previews.new()
    pcoll.my_previews_dir = ""
    pcoll.my_previews = ()
    preview_collections["main"] = pcoll

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

    bpy.types.VIEW3D_PT_tools_brush_texture.remove(sculpt_alphas_categories_prepend)

    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

if __name__ == "__main__":
    register()