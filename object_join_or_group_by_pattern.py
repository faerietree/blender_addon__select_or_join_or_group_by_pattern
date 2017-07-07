#-------------------------------------------------------------------------------
#!/usr/bin/env python
# ========= BLENDER ADD-ON =====================================================

bl_info = {
    "name":         "Join Or Group By Pattern",
    "author":       "Jon Ardaron (J.R.Balzer)",
    "version":      (2, 0),
    "blender":      (2, 6, 5),
    "location":     "View3D > Tool Shelf > Join Group By Pattern",
    "description":  "Either joins or groups that match a certain"
                    " regex or wildcard pattern. Also capable of joining"
                    " multiple variations of a pattern at once."
                    " Now with real regular expressions and influence constraints.",
    "wiki_url":     "http://wiki.blender.org/index.php/Extensions:"
                    "2.6/Py/Scripts/Object/Join_Group_By_Pattern",
    "tracker_url":  "https://projects.blender.org/tracker/index.php?"
                    "func=detail&aid=",
    "category":     "Object"
    #,"warning":      ""
}


# ------- INFORMATION ----------------------------------------------------------
# Addon-release Blender Version: 2.65 (removed access to ro context variables)
#
# Addon-Version: v20 - 2013-01-12
# Author: Jon Ardaron, FairieTale Productions GbR
#
# ------- DESCRIPTION ----------------------------------------------------------
#
# """PURPOSE"""
# JOINING OR GROUPING MESHES ACCORDING TO MESH NAME-REGEX
# (postprocessing to ACad2Obj4Blender-LISP-importer of 1D_inc)

# """WHAT IT DOES"""
# Awaits user REGEX/checkbox input for:
#
# - joining/grouping scheme: (<prefix_scheme>#?[.]?[0-9]+)
#   where <prefix_scheme> is a string and the optional '#'
#   indicates if there are multiple variants (i.e.
#   <prefix_scheme>1, <prefix_scheme>2, ... c.f. layers
#   in terms of 1D_inc's LISP add-on) and if those shall be
#   affected likewise or not at all (hence switching on kind
#   an automatic mode to look for other objects to join/group
#   from <prefix_scheme>1.001, <prefix_scheme>1.002 to
#   <prefix_scheme>1 object/group).
#
# - and whether EITHER joining OR grouping should happen. (XOR)
#   If joining is enabled (default), the only the object
#   with name <prefix_scheme>[1-9]* will remain, containing
#   all the other meshes of the corresponding objects
#   (.001, .002, ..).
#   Otherwise (if grouping is desired) a new group will be
#   created to contain all the objects matching the given regex.

# ------- LICENSING ------------------------------------------------------------
# (c) Copyright FarieTree Productions J.R.B. jan@ardaron.de
# It's free, as is, open source and property to Earth. But without warranty.
# Thus use it, improve it, recreate it and please at least keep the
# origin as in usual citation, i.e. inclucde this Copyright note.
#
# ------------------------------------------------------------------------------



#------- IMPORTS --------------------------------------------------------------#
import bpy
import re

from bpy.props import IntProperty, StringProperty, BoolProperty, EnumProperty




#------- GLOBALS --------------------------------------------------------------#
#show debug messages in blender console (that is the not python console!)
debug = False#True

#both independant, for the input-globals see register()!
case_sensitive = True
#whether to extend eventual existant selection or replace
#was useful for including explicitely first selected objs in join
extend_selection = False
#extended mode/auto expansion of or at least look-through if
#any numbering scheme can be applied to the entered pattern.
auto_expansion_to_differently_numbered = False
expanded_mode_after_howmanyfailedselections_to_abort = 100#kind a century :)

TARGET_SCENE = 0
originally_selected = {}


#------- FUNCTIONS ------------------------------------------------------------#
#COMMAND BASE FUNCTION
def main(context):
    global originally_selected
    
    #poll already checked if in_pattern is given
    #process the input now to expand possible '#'-shorthand
    #to regex wildcard [1-9]+
    processInput(context)
    #
    storeSelected(context)
    #----------#
    # auto-expand analogously
    # instead of a single act function call there are
    # several - depending on the unix_pattern input
    #----------#
    if (auto_expansion_to_differently_numbered):
        return act_autoexpanded(context)
    #else: no auto-expansion required: skip
    #act accordingly to setup inputs (group or join)
    act(context)
    return {'FINISHED'}


#PROCESS INPUT
def processInput(context):
    #count occurences of '#' from start index 1
    if (context.scene.joinorgroupbypattern_in_pattern.count('#', 1) > 0):
        if debug:
            print("Found character '#' - thus enabling special auto"
            " recognition of other objects with equal basename, but"
            " numbered differently before duplication number (i.e."
            " .001, .002, etc.). These objects will each result in"
            " their own joined mesh or created group.")
        global auto_expansion_to_differently_numbered
        auto_expansion_to_differently_numbered = True
    return {'FINISHED'}
	#pass


#STORE SELECTED
def storeSelected(context):
    global originally_selected
    global TARGET_SCENE
    if debug:
        print('storing selected objects ...',
        '\n\r--------------------------')
        print('\n\rclearing the storage dictionary')
    originally_selected = {}
    if (len(context.selected_objects) == 0):
        if debug:
            print('no selection => removing every constraint => executing in All mode')
        bpy.data.scenes[TARGET_SCENE].joinorgroupbypattern_in_selection_constraint = '1'
        return {'ABORTED'}
    #else
    if debug:
        print('refilling it')
    for o in context.selected_objects:
        if debug:
            print('stored object ', o)
        originally_selected.setdefault(o, {'obj': o})
        


#AUTOEXPANDEDACTING
def act_autoexpanded(context):
    #----------#
    # auto-expand analogously
    # instead of a single act function call there are
    # several - depending on the unix_pattern input
    #----------#
    if debug:
        print('Entered auto-expanded mode.',
        '\n\r--------------------------')
    index_start = context.scene.joinorgroupbypattern_in_auto_expansion_index_start
    index_end = context.scene.joinorgroupbypattern_in_auto_expansion_index_end
    #make it happen - multiple act calls
    unix_pattern = context.scene.joinorgroupbypattern_in_pattern
    #the '#' character is the indicator for the auto-expanded mode
    #and also shows the position of where to expand/multiply the pattern
    if (unix_pattern.find('[#]') != -1):
        if debug:
            print('Act auto-expanded function found a [#] thus will cancel expansion.'
                    ' #Line:', __LINE__)
        act(context)
        return False
    #else everything is fine
    unix_pattern_expansion_parts = unix_pattern.split('#')
    failed_selections = 0
    for index in range(index_start, index_end + 1):
        if (failed_selections > expanded_mode_after_howmanyfailedselections_to_abort):
            if debug:
                print('Failed selection efforts: ', failed_selections)
                print('Canceled further auto-expansion as there were no objects'
                'for - felt - a century.')
            return {'CANCELLED'}
        #act_try_several_amount_of_preceding_zeros (= foregoing zeros)
        #digitsleftforprecedingzeros = totaldigitcount - indexdigitcount
        #i.e. in the first looping there is no preceding zero,
        #            second              is 1
        #            third               are 2
        #     ...
        #thus the digitsTotalMax is really a maximum!
        digits_left = int(context.scene.joinorgroupbypattern_in_a_e_digits_total_max - len(str(index)))
        if (digits_left < 0):
            digits_left = 0 
        if debug:
            print('digits left = ', digits_left)
        #init
        selection_success_at_least_once = False
        for amountAntecedentZeros in range(0, digits_left + 1):
            #e.g. index = 11, totaldigitsmax = 3 => 12 - len(11) = 3 - 2 = 1 loop
            preceding_zeros_string = ""
            #builds the string of zeros dynamically
            for i in range(0, amountAntecedentZeros):
                preceding_zeros_string = str(preceding_zeros_string) + "0"
            if debug:
                print('preceding_zeros_string = ', preceding_zeros_string)
            #join the two candidates
            zeros_and_index = preceding_zeros_string + str(index)
            #finally expand the unix pattern
            expanded_pattern = unix_pattern_expansion_parts[0] + '' + zeros_and_index + unix_pattern_expansion_parts[1]
            if debug:
                print('expanded pattern = ', expanded_pattern)
            selection_result = act(context, expanded_pattern)
            if (selection_result): #and selection_result == {'FINISHED'} and len(context.selected_objects) > 0):
                selection_success_at_least_once = True
                #thus no failing (at least not included in terms of the 100 trials)
        #could we select objects at least once?
        if (selection_success_at_least_once != True):
            if debug:
                print('selection failed @ index = ', index)
            failed_selections = failed_selections + 1
    return {'FINISHED'}


#ACT
#@param string:unix_pattern is optional
#@return always returns True or False#selection_result
def act(context, unix_pattern = None):
    if debug:
        print('acting ...',
        '\n\r--------------------------')
    ############
    #preparation - selection
    ############
    #resulting_ob = None
    #ob := obMatchingPatternPrefix

    #suspended but kept for revival if API changes to much
    #for ob in bpy.scene.objects:
    #    if (ob.name.match(self.in_pattern))
    #        if (resulting_ob != None):
    #            resulting_ob = ob
    #            #continue
    #        else:
    #            bpy.ops.object.join()#joins all selected obj.

    selection_result = make_selection(context, unix_pattern);
    if (selection_result != {'FINISHED'}
            or len(context.selected_objects) == 0):
        if debug:
            print('selection could not be made (selected_objects = ',  len(context.selected_objects),')\n\r'
            ,'This round --> ABORTED\n\r'
            'if in auto-expansion mode, then we continue.'
            ' auto-expansion = ', auto_expansion_to_differently_numbered,
            '\n\r')
        return False#selection_result
    #otherwise perform a action on the selection
    if debug:
        print('selection performed successfully')
    ############
    #decide if to group or join
    ############
    if (context.scene.joinorgroupbypattern_in_mode == '0'):
        #----------#
        # join
        #----------#
        join_own_result = join(context, unix_pattern)
        if (not join_own_result):
            if debug:
                print('join_own-action not correct => aborting')
                return True#selection_result
        #else continue
        if debug:
            print('act: own join-action successful')
        if (context.scene.joinorgroupbypattern_in_tidyupnames):
            #----------#
            # tidy up - dismiss the .001, .002, .. endings if necessary
            #----------#
            tidyUpNames()
    else:
        #----------#
        # group
        #----------#
        groupname = ''
        if (len(bpy.context.selected_objects) != 0):
            groupname = getBaseName(context.selected_objects[0])
        if (not groupname or groupname is None):
            groupname = 'automatically_grouped_objects'
        group_own_result = group(context, groupname)
        if (not group_own_result):
            if debug:
                print('group (own-action-function) not successful => aborting')
            return True#selection_result
    return True#selection_result
    ############
    #act-furthermore
    ############
    #nothing so far ..
    #but a smiley :) highly underestimated


#MAKE SELECTION
def make_selection(context, unix_pattern = None):
    if debug:
        print('make_selection at your service ...',
        '\n\r--------------------------')
    #ensure_nothing_selected() ensured by pattern param#3
    # (= whether to extend selection or not)
    unix_pattern = unix_pattern or context.scene.joinorgroupbypattern_in_pattern
    if (debug):
        print(unix_pattern)
    #regex_to_unix_wildcards()
    #args = {unix_pattern, case_sensitive, extend_selection}
    bpy.ops.object.select_all(action="DESELECT")
    selection_result = select_using_configuration(context.scene.joinorgroupbypattern_in_pattern_type, unix_pattern)
    return selection_result


#JOIN
def join(context, unix_pattern):
    if (debug):
        print('joining ...')
    ############
    #make it happen
    ############
    #convert_result = bpy.ops.object.convert(target='MESH', keep_original=False)
    #convert individual objects so that convert->poll method not fails
    sel_objs_buf = context.selected_objects
    for o in sel_objs_buf:
        if (o.type != 'MESH'):
            if debug:
                print('converting to mesh ...')
            bpy.ops.object.select_all(action='DESELECT') #make sure nothing is selected
            o.select = True                       #select only the curve object
            bpy.ops.object.convert(type='MESH');         #convert it to mesh
            o.select = False
    
    #bpy.ops.object.select_all(action='DESELECT')
    selection_result = make_selection(context, unix_pattern)# or use sel_objs_buf?
    if debug:
        print('selection was successful? ', selection_result)
        print('PREVIOUSLY active_object = ', context.active_object)
    #set active_object manually
    bpy.data.scenes[TARGET_SCENE].objects.active = bpy.context.selected_objects[0]
    if debug:
        print('MANUALLY SET active_object = ', context.active_object)
    #check if all converted properly
    for o in sel_objs_buf:
        if (o.type != 'MESH'):
            print('Error: still not a mesh though converted - ', o.name)
        #o.select = True
    #join reselected pattern matching objects
    join_result = bpy.ops.object.join()
    if (join_result != {'FINISHED'}):
        if debug:
            print('joining perhaps not successful')
        return False
    if debug:
        print('joining successful')
    return True


#GROUP
def group(context, groupname):
    #analoguously
    if (debug):
        print('grouping ...')
    ############a
    #make it happen
    ############
    group_result = bpy.ops.group.create(name = groupname)
    if (not group_result or group_result != {'FINISHED'}):
        if debug:
            print('grouping not successful, group: ', groupname)
        return False
    if debug:
        print('grouping successful, group: ', groupname)
    return True
    #pass


#HELPER - TIDYUPNAMES
def tidyUpNames():
    if debug:
        print('tidying up ...')
    ############
    #fetch active object
    ############
    active_obj = isThereActiveObjectThenGet()
    if (not active_obj or active_obj is None):
        if debug:
            print('Aborting tidying up names because there is no active object.'
            ' So nothing was left after the joining or grouping?')
        return False
    ############
    #tidy up - dismiss the .001, .002, .. endings if necessary
    ############
    if debug:
        print('Object-name before refactoring: ', active_obj.name)
    cleanname = getBaseName(active_obj)
    if (cleanname and cleanname != active_obj.name):
        if debug:
            print('renaming')
        active_obj.name = cleanname
        if debug:
            print('renaming *done*')
    #debug
    if debug:
        print('Object-name after refactoring: ', active_obj.name)
    return True


###############################
# DYNAMIC SELECT FUNCTIION CALL
##
# one out of the following select functions is called
###############################

#SELECT BY WILDCARDS---------------------------------------------
def select_by_wildcards(unix_pattern): #given by blender
    global extend_selection
    global case_sensitive
    
    if debug:
        print('select_by_wildcards at your service ...')
    #select
    selection_result = bpy.ops.object.select_pattern(
        pattern = unix_pattern,
        case_sensitive = case_sensitive,
        extend = extend_selection
    )
    return selection_result

#DESELECT IF ORIGINALLY NOT BEEN SELECTED
def deselect_ifOriginallyNotBeenSelected(*args):
    global originally_selected
    if debug:
        print('deselect_ifOriginallyNotBeenSelected at your Service ...')
    #only if selection constraint to selected objects only
    if bpy.context.scene.joinorgroupbypattern_in_selection_constraint == '0':
        if debug:
            print('deselecting some of the objects not within the selection constraint')
    
        #could get expensive, so avoid it
        for sel_o in bpy.context.selected_objects:
            if debug:
                print('investigating if sel_o (', sel_o, ') has been originally selected')
            hasBeenOriginallySelected = False
            for originally_sel_o in originally_selected:
                if originally_sel_o.name == sel_o.name:
                    #okay, then it was within the selection constraint -> all fine with that
                    hasBeenOriginallySelected = True
            if not hasBeenOriginallySelected:
                #deselect using orig. stored obj as context is read-only
                if debug:
                    print('deselcting o', originally_sel_o)
                originally_sel_o.select = False
            
    

#SELECT BY REGEX-------------------------------------------------
def select_by_regex(pattern):
    if debug:
        print('select_by_regex at your Service ...')
        #print(selection_pool['0'], ' == ? ', selection_pool[bpy.context.scene.joinorgroupbypattern_in_selection_constraint])
        #print('selection_constraint = ', bpy.context.scene.joinorgroupbypattern_in_selection_constraint)
    #
    within_these_objects = selection_pool[bpy.context.scene.joinorgroupbypattern_in_selection_constraint]
    selection_pool_L = len(within_these_objects)
    #debug
    if debug:
        print('selection_constraint = ',within_these_objects)
        print('selection_pool_L = ', selection_pool_L)
    
    selectedAtLeastOne = False
    for obj in within_these_objects:
        if debug:
            #print('Item ', obj, ' out of ', selection_pool_L)
            print('does ', obj.name, ' match ', pattern)
        if (re.match(pattern, obj.name)):
            if debug:
                print('matched object: ', obj.name)
            obj.select = True
            selectedAtLeastOne = True
    if not selectedAtLeastOne:
        return {'ABORTED'}
    return {'FINISHED'}




def nop(*args):
    pass

#CONFIGURATION OBJECTS-------------------------------------------
#using predefined static configurations - has to be after function definition
select_configurations = {
    #'wildcards'
    '1': (select_by_wildcards, deselect_ifOriginallyNotBeenSelected)
    #static, but extendable ( f1, f2, .. fx)
    #'regex'
    ,'0': (select_by_regex, nop)
}
selection_pool = {
    #'all objects'
    '1': bpy.data.scenes[TARGET_SCENE].objects
    #'selected_only'
    ,'0': originally_selected #== bpy.context.selected_objects originally
}



################################
# THIS FUNCTION HANDLES WHICH OF THE TWO SELECT PATHS IS TO BE FOLLOWED
##
#the dynamic function
################################

#SELECT USING CONFIGURATION
def select_using_configuration(config, unix_pattern, *args, **kwargs):
    if debug:
        print('select_using_configuration at your Service ...')
    #default
    selection_result = {'ABORTED'}
    i = -1
    for op in select_configurations[config]:
        i = i + 1
        if debug:
            print('config = ', config, ' i = ', i, 'op = ', op)
        result = op(unix_pattern, *args, **kwargs)
        #WITH ASTERISK SEEMS TO WORK
        if (i == 0):
            selection_result = result
    return selection_result
        



#using dynamically buildable functions
#SELECT
#def select(funcsToCall_arrOfstr, *args, **kwargs):
#    for func in funcsToCall_arrOfstr:
#        globals()[func](args, kwargs)

#SELECT
#def select_callAppropriate_str(funcsToCall_str, *context, **kwregex):
#    for func in funcsToCall_str.split():
#        globals()[func](*context, **kwargs)







#HELPER - ISTHERESELECTION
def isThereSelectionThenGet():
    if debug:
        print('isThereSelectionThenGet at your Service ...')
    #opt. check if selection only one object (as is to be expectat after join)
    sel = bpy.context.selected_objects
    if (debug):
        print('Count of objects in selection (hopefully 1): ', len(sel))
    if (sel is None or not sel):
        if debug:
            print('No selection! Is there nothing left by join action? *worried*',
            '\n\raborting renaming ...')
        return False
    #else make remaining object (or one out of them) active
    bpy.data.scenes[TARGET_SCENE].objects.active = sel[0]
    #deliver the selection
    return sel


#HELPER - ISTHEREACTIVEOBJECT
def isThereActiveObjectThenGet():
    if debug:
        print('isThereActiveObjectThenGet at your Service ...')
    
    #get active object of context
    active_obj = bpy.context.active_object
    if (active_obj is None or not active_obj):
        if debug:
            print('No active object -',
            ' trying to make the first object of the selection the active one.')
        #check if selection and get
        sel = isThereSelectionThenGet()
        #make first object active (usually it should only be 1 object)
        bpy.context.object.active = sel[0]
    active_obj = bpy.context.active_object
    if (active_obj is None or not active_obj):
        if debug:
            print('Still no active object! Aborting renaming ...')
        return False
    #deliver the active object
    return active_obj


#HELPER - GETBASENAME
#@return string:basename aka cleanname
def getBaseName(obj):
    if debug:
        print('getBaseName at your Service ...')
    
    obj_basename_parts = obj.name.split('.')
    obj_basename_parts_L = len(obj_basename_parts)
    if debug:
        print('Last part: ', obj_basename_parts[obj_basename_parts_L - 1])
    if (obj_basename_parts_L > 1
    and re.match('[0-9]{3}$', obj_basename_parts[obj_basename_parts_L - 1])):
        if debug:
            print('determining base name')
        #attention: last item is left intentionally
        cleanname = ''
        for i in range(0, obj_basename_parts_L - 1):
            cleanname += obj_basename_parts[i]
        #done this strange way to avoid unnecessary GUI updates
        #as the sel.name fields in the UI may be unnecessarily updated on change ...
        if debug:
            print('determining *done*, determined basename: ', cleanname)
        return cleanname
    else:
        if debug:
            print('already tidied up *done*, basename: ', obj.name)
        return obj.name
    

#------- CLASSES --------------------------------------------------------------#


#/**
# * JoinOrGroupMatchingObjects
# *
# * Wraps some general attributes and some specific ones
# * like the actual content of the regex input field.
# *                               inheritance
# */
class OBJECT_OT_Join_Or_Group_By_Wildcard(bpy.types.Operator):
    """Performs the operation (i.e. joining or grouping) according to your settings."""
    #=======ATTRIBUTES=========================================================#
    bl_idname = "object.join_or_group_by_pattern"
    bl_label = "Either join or group objects matching a"
    " regex <prefix_scheme>#?([.][0-9]+)* where <prefix_scheme> may be a regex too."
    bl_context = "objectmode"
    bl_register = True
    bl_undo = True
    
    #=======CONSTRUCTION=======================================================#
    #def __init__(self):
    #=======METHODS============================================================#
    @classmethod
    def poll(cls, context):#it's the same without self (always inserted before)
        SCENE = 0
        #check the context
        #context does not matter here
        #return context.active_object is not None
        input_pattern = context.scene.joinorgroupbypattern_in_pattern
        if (input_pattern != ""):
            if (input_pattern.find('#') != -1):
                    #and input_pattern.find('\[#\]') == -1):
                #we're in auto-expansion mode, thus
                #adjust other inputs to keep up integrity
                in_auto_expansion_keep_up_integrity(context)
                #
                return True
            return True

        #else:
        #if debug:
        #    print('No pattern given. Shall join every object? Doing so.')
        context.scene.joinorgroupbypattern_in_pattern = '*'
        #return True
        #recheck it, otherwise the button is deactivated, "else:" was the reason! really strange
        #return cls.poll(context = context)
        return True

    def execute(self, context):
        main(context)
        return {'FINISHED'}





#/**
# * GUI Panel
# *
# * Two or more inputs: 1x chebox, 1x text input for the pattern.
# * Extends Panel.
# */
class VIEW3D_PT_tools_joinorgroup_by_pattern(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Join Group By Pattern'
    bl_context = 'objectmode'
    bl_options = {'DEFAULT_CLOSED'}
    #DRAW
    def draw(self, context):
        s = context.scene
        in_mode_str = 'Join'
        #get a string representation of enum button
        if debug:
            print('Mode: ', s.joinorgroupbypattern_in_mode)
        if (s.joinorgroupbypattern_in_mode != '0'):
            in_mode_str = 'Group'
        layout = self.layout
        col = layout.column(align = True)
        col.row().prop(s, 'joinorgroupbypattern_in_mode', expand = True)
        
        #textfield
        layout.prop(s, 'joinorgroupbypattern_in_pattern', text = 'Pattern')
        
        #get a string representation of enum button
        in_pattern_type_str = 'RegEx'
        if debug:
            print('Pattern Type: ', s.joinorgroupbypattern_in_pattern_type)
            print('prop access:', s.joinorgroupbypattern_in_pattern_type)
        if (s.joinorgroupbypattern_in_pattern_type != '0'):
            in_pattern_type_str = 'Wildcards'
        layout = self.layout
        col = layout.column(align = True)
        col.row().prop(s, 'joinorgroupbypattern_in_pattern_type', expand = True)
        
        
        
        
        #splitbutton for enums (radio buttons) ...
        row = layout.row(align = True)
        #only relevant if mode set to join => active (additional option)
        row.active = (in_mode_str == 'Join')
        row.prop(s, 'joinorgroupbypattern_in_tidyupnames')
        if (s.joinorgroupbypattern_in_pattern.find('#') != -1
                and s.joinorgroupbypattern_in_pattern.find('\[#\]') == -1):
            ############
            #auto expansion
            ############
            col = layout.column(align = True)
            col.label(text = 'Auto-Expansion:')
            col.row().prop(s, 'joinorgroupbypattern_in_auto_expansion_index_start')
            col.row().prop(s, 'joinorgroupbypattern_in_auto_expansion_index_end')
            col.row().prop(s, 'joinorgroupbypattern_in_a_e_digits_total_max')
        
        
        #get a string representation of enum button
        in_influence_str = '' #default is selected only
        if debug:
            print('Influence: ', s.joinorgroupbypattern_in_selection_constraint)
        if (s.joinorgroupbypattern_in_selection_constraint == '1'):
            in_influence_str = ' all'
        layout = self.layout
        col = layout.column(align = True)
        col.row().prop(s, 'joinorgroupbypattern_in_selection_constraint', expand = True)
        
        
        
        #submit, trigger chosen action
        row = layout.row(align = True)
        label = in_mode_str + in_influence_str + " matching objects"
        row.operator('object.join_or_group_by_pattern', icon='FILE_TICK', text = label)
        
        
        
        
        




#------- CALLBACKS - INPUT - AUTO EXPANSION --------------------------------------#
#cALLBACK
def callback_in_pattern_changed(self, context):
    s = context.scene
    if (s.joinorgroupbypattern_in_pattern.find('#') != -1
            and s.joinorgroupbypattern_in_pattern.find('\[#\]') == -1):
        ############
        #auto expansion
        ############
        #callback_in__changed(context)
        #callback_in__changed(context)
        #callback_in__changed(context)
        pass
#
def callback_in_auto_expansion_index_start_changed(self, context):
    in_auto_expansion_keep_up_integrity(context)
#
def callback_in_auto_expansion_index_end_changed(self, context):
    in_auto_expansion_keep_up_integrity(context)
#
def callback_in_a_e_digits_total_max_changed(self, context):
    in_auto_expansion_keep_up_integrity(context)
    #return None #required by update callbacks!
#
def in_auto_expansion_keep_up_integrity(context):
    #SCENE = 0
    #we're in auto-expansion mode, thus
    digits_max = context.scene.joinorgroupbypattern_in_a_e_digits_total_max
    index_start = context.scene.joinorgroupbypattern_in_auto_expansion_index_start
    index_end = context.scene.joinorgroupbypattern_in_auto_expansion_index_end
    if (len(str(index_end)) > digits_max):
        max_possible_rounded = '1'
        for i in range(0, digits_max):
            max_possible_rounded = max_possible_rounded + '0'
        index_end = int(max_possible_rounded) - 1
        context.scene.joinorgroupbypattern_in_auto_expansion_index_end = index_end
        #bpy.data.scenes[SCENE].joinorgroupbypattern_in_auto_expansion_index_end = index_end
    if (index_start > index_end):
        index_start = index_end - 1
        context.scene.joinorgroupbypattern_in_auto_expansion_index_start = index_start
        #bpy.data.scenes[SCENE].joinorgroupbypattern_in_auto_expansion_index_start = index_start
    return None







#------- GENERAL BLENDER SETUP FUNCTIONS --------------------------------------#
#REGISTER
def register():
    bpy.utils.register_module(__name__)
    #bpy.utils.register_class(OBJECT_OT_JoinOrGroupByWildcard)
    #bpy.utils.register_class(VIEW3D_PT_tools_joinorgroup_by_pattern)
    #bpy.types.Scene.joinorgroupbypattern_in_pattern = '1DLay#([.][0-9]+)*'
    bpy.types.Scene.joinorgroupbypattern_in_pattern = StringProperty(
        name = 'Pattern'
        ,description = 'Regular expression or UNIX-wildcards. Regex: .* matchs every char no matter how often [.]+ matches a . once or more often. A[B]? matches A or AB. Wildcards: a*d.LISP matches abc.LISP, azzcxd.LISP, ... but a?c matches acc, adc, azd, ...'
        ,default = '1D_LAY#([.][0-9]*)?$'
        ,update = callback_in_pattern_changed
    )
    #important: interprete the '#' to internally expand it to [1-9]+ - NO - just
    #run sequentially for 1-9 or 001, 002,... 999
    #it's just a short hand for the user not familiar with regex
    bpy.types.Scene.joinorgroupbypattern_in_mode = EnumProperty(
        name = "Mode",
        description = "Select whether to join the objects or rather to organize them in a group.",
        items = [
            ("0", "Join", ""),
            ("1", "Group", "")
        ],
        default='0'
    )
    bpy.types.Scene.joinorgroupbypattern_in_pattern_type = EnumProperty(
        name = "Pattern Type",
        description = "If Pattern Type is a RegEx => more powerful. Else Wildcards => Quicker. The syntax and its meaning differs!! Asterisk * when used with regex means the expression before must be matched 0 or x times. Questionm. ? flags the expr/char before! as optional.",
        items = [
            ("0", "RegEx", ""),
            ("1", "Wildcards", "")
        ],
        default='0'
    )

    bpy.types.Scene.joinorgroupbypattern_in_selection_constraint = EnumProperty(
        name = "Influence",
        description = "Influecne: Choose if all or merely the selected objects shall be included.",
        items = [
            ("0", "Selected", "")   #list-item '0'
            ,("1", "All", "")        #list-item '1'
            #,("2", "Global", "")      #list-item '2' #TODO
        ],
        default='0'
    )


    bpy.types.Scene.joinorgroupbypattern_in_tidyupnames = BoolProperty(
        name = "Tidy up names",
        description = "Whether to shorten the resulting joined objects name or not.",
        default = True
    )

    #auto-expaned mode only
    bpy.types.Scene.joinorgroupbypattern_in_auto_expansion_index_start = IntProperty(
        name = "Start",
        description = "AUTO-EXPANSION: by default starting at zero (0)."
        " However you may want to join half of the objects - but the other half you want to be grouped."
        " This is what these start and end values can be used for. Use this value to set the lower bound"
        " of the effected objects.\n\r"
        "EXAMPLE:\n\r"
        "Assume default values and the pattern 'PREFIX_LAYER#_SUBCRITERIA[.][0-9]+' - then the following"
        " will happen: Object PREFIX_LAYER0_SUBCRITERIA, PREFIX_LAYER0_SUBCRITERIA.000"
        " and PREFIX_LAYER0_SUBCRITERIA.001, ... will be affected by the operation and thus being joined"
        " or grouped to a joined object/group 'PREFIX_LAYER0_SUBCRITERIA'.\n\r"
        "Now the expansion gets into it and it will perform the same operation for the objects"
        " PREFIX_LAYER1_SUBCRITERIA, PREFIX_LAYER1_SUBCRITERIA, ... and join/group them according to the"
        " settings.\n\r"
        "This story now continues up to the point of time, when the addon detects that there are no more"
        " objects found which match the pattern for a while. (after 100 loops without objects in attempted"
        " selection).\n\r"
        "Hence you can use the start and end settings to control the range of the expansion."
        ,min = 0
        ,max =  999000
        #,options = {'HIDDEN'}
        ,update = callback_in_auto_expansion_index_end_changed
    )
    bpy.types.Scene.joinorgroupbypattern_in_auto_expansion_index_end = IntProperty(
        name = "End",
        description = "AUTO-EXPANSION: By default auto-detection stops after there are no more objects found."
        " However you may want to join half of the objects - but the other half you want to be grouped."
        " This is what these start and end values can be used for. Use this value to set the upper bound"
        " of where to definitely stop the operation.\n\r"
        "EXAMPLE:\n\r"
        "Assume default values and the pattern 'PREFIX_LAYER#_SUBCRITERIA[.][0-9]+' - then the following"
        " will happen: Object PREFIX_LAYER0_SUBCRITERIA, PREFIX_LAYER0_SUBCRITERIA.000"
        " and PREFIX_LAYER0_SUBCRITERIA.001, ... will be affected by the operation and thus being joined"
        " or grouped to a joined object/group 'PREFIX_LAYER0_SUBCRITERIA'.\n\r"
        "Now the expansion gets into it and it will perform the same operation for the objects"
        " PREFIX_LAYER1_SUBCRITERIA, PREFIX_LAYER1_SUBCRITERIA, ... and join/group them according to the"
        " settings.\n\r"
        "This story now continues up to the point of time, when the addon detects that there are no more"
        " objects found which match the pattern for a while. (after 100 loops without objects in attempted"
        " selection).\n\r"
        "Hence you can use the start and end settings to control the range of the expansion."
        #,options = {'HIDDEN'}
        ,min = 1
        ,max = 1000000
        ,default = 999 # to make sure this will not be a never ending story
        ,update = callback_in_auto_expansion_index_end_changed
    )
    bpy.types.Scene.joinorgroupbypattern_in_a_e_digits_total_max = IntProperty(
        name = "Max digits",
        description = "Speeds up the script. Maximum of digits at position of auto-expansion (indicated"
        " by "#") needed for inserting correct amount of preceding zeros. It"s the upper limit, i.e. for a"
        " value of 3 the the script would try 1-expansion as well as expanding to both 01 and 001 - 2, 02,"
        " 002 respectively - and so on ..."
        ,default = 3
        ,min = 0
        ,max = 7
        ,update = callback_in_a_e_digits_total_max_changed
    )

    #pass


#UNREGISTER
def unregister():
    bpy.utils.unregister_module(__name__)
    #bpy.utils.unregister_class(OBJECT_OT_JoinOrGroupByWildcard)
    #bpy.utils.unregister_class(VIEW3D_PT_tools_joinorgroup_by_pattern)
    #please tidy up
    del bpy.types.Scene.joinorgroupbypattern_in_mode
    del bpy.types.Scene.joinorgroupbypattern_in_pattern
    del bpy.types.Scene.joinorgroupbypattern_in_pattern_type
    del bpy.types.Scene.joinorgroupbypattern_in_selection_constraint
    del bpy.types.Scene.joinorgroupbypattern_in_tidyupnames
    del bpy.types.Scene.joinorgroupbypattern_in_auto_expansion_index_start
    del bpy.types.Scene.joinorgroupbypattern_in_auto_expansion_index_end
    del bpy.types.Scene.joinorgroupbypattern_in_a_e_digits_total_min 
    del bpy.types.Scene.joinorgroupbypattern_in_a_e_digits_total_max
    #pass


#------- PROCEDURAL -----------------------------------------------------------#
if __name__ == "__main__":
    #unregister()
    register()
    # test call
    #bpy.ops.object.join_or_group_by_pattern()