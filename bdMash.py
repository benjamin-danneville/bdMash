import maya.cmds as cmds
import maya.mel as mel

import MASH.api as mapi

############
## GLOBAL ##
############

brush_grp_name = "BRUSHSTROKES"

geo_grp_list = []
brush_grp_list = []

###############
## RECURSIVE ##
###############

def add_geo(geo_grp, geo_list):
    for geo in cmds.listRelatives(geo_grp):
        if cmds.objectType(cmds.listRelatives(geo)[0]) == "mesh":
            geo_list.append(geo)
        else:
            add_geo(geo, geo_list)

##############
## FUNCTION ##
##############

def Listing():
    selection = cmds.ls(sl=True)

    geo_grp_list.clear()
    brush_grp_list.clear()

    #Add check (Number of selected, and if brush name is not present)
    for grp in selection:
        if brush_grp_name in grp:
            brush_grp_list.append(grp)
        else:
            geo_grp_list.append(grp)

def CheckUp():
    temp_checkUp_state = 1

    for brush_grp in brush_grp_list:
        for brush in cmds.listRelatives(brush_grp):
            #Reseting to 0 to check each brush state
            state = 0

            if cmds.getAttr(brush + "Shape.castsShadows") == 1:
                cmds.setAttr(brush + "Shape.castsShadows", 0)

            if cmds.getAttr(brush + "Shape.aiSelfShadows") == 1:
                cmds.setAttr(brush + "Shape.aiSelfShadows", 0)
            
            #Get materials so that I can check if it has the aiUserDataColor
            cmds.select(brush)
            brush_nodes = cmds.ls(sl = True, dag = True, s = True)
            shadeEng = cmds.listConnections(brush_nodes , type = 'shadingEngine')
            material = cmds.ls(cmds.listConnections(shadeEng ), materials = True)

            for node in cmds.listHistory(material):
                if cmds.nodeType(node) == 'aiUserDataColor':
                    state = 1
                    aiUDC_node = node
            
            if state == 1:
                cmds.setAttr(aiUDC_node + ".attribute", "colorSet", type = "string")
            else:
                print (brush + " doesn't have an aiUserDataColor as a BaseColor")
                temp_checkUp_state = 0

    cmds.select(d=True)

    return temp_checkUp_state

def Mash():
    UVMESH_grp_name = "bd_UVMESH_grp"
    if not cmds.objExists(UVMESH_grp_name):
        cmds.group(em=True, name=UVMESH_grp_name)
    for geo_grp in geo_grp_list:

        bc_state = 0

        geo_list = []
        add_geo(geo_grp, geo_list)

        #Get BaseColor
        cmds.select(geo_list[0])
        geo_nodes = cmds.ls(sl = True, dag = True, s = True)
        shadeEng = cmds.listConnections(geo_nodes , type = 'shadingEngine')
        material = cmds.ls(cmds.listConnections(shadeEng ), materials = True)
        geo_node_output = cmds.listConnections(material, type = 'file', p=True)
        if geo_node_output != None:
            for i in range(len(cmds.listConnections(material, type = 'file'))):
                if cmds.isConnected(geo_node_output[i], material[0] + ".baseColor") == 1:
                    bc_state = 1
                    geo_bc_file = cmds.listConnections(material, type = 'file')[i]

        #if there is no baseColor, we indicate it
        if bc_state != 1:
            print (geo_grp + " material has no file plugged into the Base Color")
        
        cmds.select(geo_list)

        cmds.duplicate()
        mel.eval('CombinePolygons;')
        #Rename using selection
        UVMESH_name = geo_grp[0:-3] + "UVMESH_geo"
        cmds.rename(UVMESH_name)
        cmds.parent(UVMESH_name, UVMESH_grp_name)
        cmds.hide(UVMESH_name)

        #Check if a brush grp is selected ! (maybe multiples configuration) (Get the groupe name in the mash_name)
        cmds.select(cmds.listRelatives(brush_grp_list[0]))
        MASH_geo_name =  geo_grp[0:-3] + "MASH_geo"

        mashNetwork = mapi.Network()
        mashNetwork.createNetwork(name=MASH_geo_name)

        #Adding all nodes
        mash_node_random = mashNetwork.addNode("MASH_Random")
        mash_node_color = mashNetwork.addNode("MASH_Color")

        #DISTRIBUTE
        cmds.setAttr(mashNetwork.distribute + ".arrangement", 4)
        cmds.connectAttr(UVMESH_name + 'Shape.worldMesh[0]', mashNetwork.distribute + ".inputMesh", f=True )
        #Numbers of points
        cmds.setAttr(mashNetwork.distribute + ".pointCount", 100)
        #Method
        cmds.setAttr(mashNetwork.distribute + ".meshType", 3)

        #ID
        if len(cmds.listRelatives(brush_grp_list[0])) > 1 :
            cmds.setAttr(mashNetwork.waiter + "_ID.numObjects", len(cmds.listRelatives(brush_grp_list[0])))

        #RANDOM
        random_attr_name_list = ["positionX", "positionY", "positionZ", "rotationX", "rotationY", "rotationZ", "scaleX", "scaleY", "scaleZ"]
        random_attr_value_list = [0.2, 0.2, 0.2, 0, 0, 0, 0.5, 0.5, 0.5]
        for i in range(len(random_attr_name_list)):
            cmds.setAttr(mash_node_random.name + "." + random_attr_name_list[i], random_attr_value_list[i])

        #Color
        cmds.connectAttr(UVMESH_name + '.worldMatrix[0]', mash_node_color.name + ".uvMatrix", f=True )
        try:
            cmds.connectAttr(geo_bc_file + '.outColor', mash_node_color.name + ".color", f=True )
        except UnboundLocalError:
            pass
        #Getting colors to show
        cmds.setAttr(mashNetwork.waiter + "_ReproMeshShape.aiExportColors", 1)
        
############
## BUTTON ##
############

def MashButton(_):
    Listing()
    checkUp_state = CheckUp()

    if checkUp_state == 1:
        Mash()
    else:
        print ("Please check that your MASH objects have the right properties")

############
## WINDOW ##
############

bdMash_win = 'bdMash'

if cmds.window(bdMash_win, exists=True):
    cmds.deleteUI(bdMash_win)

# Start with the Window 
cmds.window(bdMash_win, widthHeight=(300, 30)) 
# Add a single column layout to add controls into 
cmds.columnLayout(adjustableColumn=True) 

cmds.text("\n1 - Select all the groups you want to apply Mash to", align='left')
cmds.text("2 - Select the group containing the meshes that will be used for the MASH called 'BRUSHSTROKES'", align='left')
cmds.text("\n3 - Click the Mash Button !\n", align='left')

# Add controls to the Layout 
cmds.button( label="Mash", command=MashButton) 
# Display the window 
cmds.showWindow(bdMash_win)