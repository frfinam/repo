import base64
import numpy as np 
import pandas as pd

import folium
from folium import plugins


import rasterio as rio #library for GeoTIFF and GIS formats

import geopandas as gpd #used to change crs coordinates

#import for webapp
import streamlit as st
from streamlit_folium import st_folium

APP_TITLE = 'Steel Structures Prefabr. - Web Map'
APP_SUB_TITLE = 'RDCG Project'

def display_map():

    # To be used to convert onedrivelink in download url
    def create_onedrive_directdownload (onedrive_link):
        data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
        data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
        resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
        return resultUrl


    ########################################### START: CREATE A TABLE OF PREFABRICATION PROGRESS #########################################################

    #Connect to rddump of easystructure dataview to have prefabrication progress
    cols   = ['Area', 'Structure', 'dp_mp', 'Name', 'RD', 'am_serial_no', 'Weight', 'DESCRIP', 'Vendor', 'fab_start_date', 'fab_completed_date', 'srn_date']
    df_one_drive = "https://1drv.ms/u/s!AiiyfzN3UvpehmtMgdLsh8aMt813?e=QyoUBi"
    df_link = create_onedrive_directdownload (df_one_drive)
    df = pd.read_csv(df_link, encoding='ISO-8859-1', low_memory=False)[cols]


    # add a Main Description of marks by few main category (MAIN STEEL, GRATINGS,..)
    df["MainDescr"] = np.where(df['DESCRIP'].str.contains('STEEL'),"MAIN STEEL", np.where(df['DESCRIP'].str.contains('LADDER|HANDRAIL|STAIR'),"HRAIL & LADDER & STAIR", np.where(df['DESCRIP'].str.contains('GRATING'),"GRATINGS","OTHER")))



    #ATTENZIONE I VALORI CHE ESCONO SONO STRANI...........CONTROLLA
    # add status and qty of fabrication started and completed
    df["fab_start_status"] = np.where(df['fab_start_date'].isna(),0 ,1)
    df["fab_completed_status"] = np.where(df['fab_completed_date'].isna(),0, 1)
    df[["Weight", "fab_start_status","fab_completed_status"]]= df[["Weight", "fab_start_status","fab_completed_status"]].apply(pd.to_numeric)

    df["Fabric_Started_Qty"] = df['fab_start_status']*df['Weight']
    df["Fabricated_Qty"] = df['fab_completed_status']*df['Weight']


    # create a table with qty summarized by Structure Tag
    df_Prfb = df.groupby("Structure")[["Weight", "Fabric_Started_Qty","Fabricated_Qty"]].sum().div(1000).round(2).reset_index()

    ########################################### END : CREATE A TABLE OF PREFABRICATION PROGRESS #########################################################
    #####################################################################################################################################################






    ########################################### START: CREATE A TABLE OF PROCUREMENT PROGRESS #########################################################
    columns_selected = ["ROUTING_METHOD_CODE","Requisition number","Req Pos","PO Number","Req Sub Pos","ISH Pos","ISH Sub Pos","PO Long description",  "Tag Number", "Ident Description", "Supplier Code","Destination", "Forecasted Date", "Actual Date"]

    #file = "C:/Users/ffinamore/Desktop/Folium/Input/IEETDE01.xlsx"
    #  option from one drive
    file_one_drive ="https://1drv.ms/x/s!AiiyfzN3UvpehmYbSBx3aFBcaXGr?e=36n4ud"
    file = create_onedrive_directdownload(file_one_drive)
    #file_dp = "C:/Users/ffinamore/Desktop/Folium/Input/Weight_DP_Item.xlsx"
    #  option from one drive
    file_dp_one_drive ="https://1drv.ms/x/s!AiiyfzN3UvpehmPWAlUb31CFi26b?e=mvvWCB"
    file_dp = create_onedrive_directdownload(file_dp_one_drive)



    #expediting report

        
    de = pd.read_excel(file, engine='openpyxl',  skiprows=8, header=0, usecols=columns_selected)


    #weight of delivery package

        
    dp = pd.read_excel(file_dp, engine='openpyxl', header=0)
    dp['Procurem_Key1'] = dp['PO Number'].map(str)+"_"+dp['Req Pos'].map(str)+"_"+dp['Req Sub Pos'].map(str)+"_"+dp['ISH Pos'].map(str)+"_"+dp['ISH Sub Pos'].map(str)
    dp1 = dp[['Procurem_Key1','Weight(Kg)']]  



    #select procurement data for steel structures scope of work of RDCG 
    df1 = de[((de['ROUTING_METHOD_CODE'].str.contains("RDCG")) & (de['PO Long description'] == "STEEL STRUCTURES"))]


    #select just the start of shipping and site arrival
    df2 = df1[(df1['Destination']=="JOBSITE ARRIVAL")| (df1['Destination']=="INSPECTION")]
    df2['Procurem_Key'] = df2['PO Number'].map(str)+"_"+df2['Req Pos'].map(str)+"_"+df2['Req Sub Pos'].map(str)+"_"+df2['ISH Pos'].map(str)+"_"+df2['ISH Sub Pos'].map(str)



    df2['ActualStatus'] = np.where(df2['Actual Date'].isna(), 0, 1)


    #ATTENZIONE VIENE NA AL PESO RISULTATO DEL JOIN....
    df3 = df2.join(dp1, lsuffix='Procurem_Key', rsuffix='Procurem_Key1')

    df4= df3.drop(columns=['Procurem_Key1'])

    df4['ShippedWeight'] = np.where(df4['Destination'] =="INSPECTION" , (df4['ActualStatus'] * df4['Weight(Kg)']), 0)          
    df4['AtSiteWeight'] = np.where(df4['Destination'] =="JOBSITE ARRIVAL" , (df4['ActualStatus'] * df4['Weight(Kg)']), 0)     


    df_Exp = df4.groupby("Tag Number")[["ShippedWeight", "AtSiteWeight"]].sum().reset_index()

    df_Exp.rename(columns={'ShippedWeight': 'Shipped_Qty','AtSiteWeight': 'At_Site_Qty'}, inplace=True)
    ########################################### END : CREATE A TABLE OF PROCUREMENT PROGRESS #########################################################
    ##################################################################################################################################################




    ########################################### START: LOAD IMAGES (ITEMS SNAPSHOT AND MAP) #########################################################
    # file path of the screenshots of the pr/str (png) from local folder
    #screens_path = "C://Users//ffinamore//Desktop//Folium//ScreenShot//"

    # file path of the screenshots of the pr/str (png)  from cloud
    screens_path = "https://github.com/frfinam/scrsht/blob/main/"

    # file path of the image (png) to add as tile layer
    #img_MNA_SAT = "C://Users//ffinamore//OneDrive - TEN//20 - Projects//082755C - Neste RDCG Rotterdam//05 - WFM//01 - Civil//06 - Mapping//Sat//23-05-09_MNA//Factual Plot Plan_MNA_05.05.2023_BI_modified.tif"
    #  option from one drive
    img_MNA_SAT_one_drive = "https://1drv.ms/i/s!AiiyfzN3UvpehmHk8eOdXHPb78m-?e=5fgt3M"
    img_MNA_SAT = create_onedrive_directdownload (img_MNA_SAT_one_drive)

    # manage the TIF file 
    with rio.open(img_MNA_SAT) as src:
        img1 = src.read()
    ########################################### END: LOAD IMAGES (ITEMS SNAPSHOT AND MAP) #########################################################
    ##################################################################################################################################################







    ########################################### START: CALCULATE OSM LAT/LONG OF 3D ITEMS #########################################################
    # Amersfoort / RD New -- Netherlands - Holland - Dutch  : EPSG "28992" OR EPSG"7415"
    EPSG_System = "28992"


    #delta local cad reference and global
    ELRPC = E_local_reference_point_cad_m = 1000
    NLRPC = N_local_reference_point_cad_m = 1000
    EARPC = E_absolute_reference_point_cad_m = 60602.328
    NARPC = N_absolute_reference_point_cad_m = 443433.61

    #there is a gap between EW/NS coordinates of cad with respect to the 3d coordinates
    ED = E_delta_local_cad_local_3d_m = -1500
    ND = N_delta_local_cad_local_3d_m = 300


    #df_3D = pd.read_csv("C://Users//ffinamore//Desktop//Folium//Input//3D_Item.csv")
    #  option from one drive
    df_3D_one_drive = "https://1drv.ms/u/s!AiiyfzN3UvpehmKgEVggK5U8u88O?e=YhiFlx"
    df_3D_link = create_onedrive_directdownload (df_3D_one_drive)

    df_3D = pd.read_csv(df_3D_link, encoding='ISO-8859-1')

    #create a point from two columns 
    # and set its coordinate reference system (CRS)
    gdf = gpd.GeoDataFrame(
        df_3D, geometry=gpd.points_from_xy(((df_3D['EW_(mm)']/1000) + ED+ (EARPC-ELRPC)), ((df_3D['NS_(mm)']/1000)+ ND + (NARPC-NLRPC))), crs=str(EPSG_System))

    #print(gdf.head())
    #print(gdf)


    # change the projection of geodf to OpenStreetMap
    geodf = gdf.to_crs('EPSG:4326')

    geodf['Lat']=geodf['geometry'].y
    geodf['Long']=geodf['geometry'].x


    #print(geodf)
    ########################################### END: CALCULATE OSM LAT/LONG OF 3D ITEMS #########################################################
    ##################################################################################################################################################





    ########################################### START: POPULATE TAG TABLES USED IN MAP #########################################################
    # open the list of tags
    #df_Tag_List = pd.read_csv("C://Users//ffinamore//Desktop//Folium//Input//MainStructures.csv"
    # open the list of tags option from one drive
    df_Tag_List_one_drive = "https://1drv.ms/u/s!AiiyfzN3UvpehmlCvqma5PczBH-o?e=AZGery"
    df_Tag_List_one_link = create_onedrive_directdownload (df_Tag_List_one_drive)
    df_Tag_List = pd.read_csv(df_Tag_List_one_link,encoding='ISO-8859-1')


    #add fabrication status from ESS to tag list
    df_MS_1 = pd.merge(df_Tag_List, df_Prfb, how='left', left_on=['Tag'], right_on=['Structure'])

    #add expediting status from SMAT to tag list
    df_MS_2 = pd.merge(df_MS_1, df_Exp, how='left', left_on=['Tag'], right_on=['Tag Number'])

    #add lat and long of the tag
    df_MS = pd.merge(df_MS_2, geodf, how='left', left_on=['Tag'], right_on=['TAG'])

    #replace NaN with 0  NON FUNZIONA
    df_MS.fillna(0)

    print(df_MS)
    ########################################### END: POPULATE TAG TABLES USED IN MAP #########################################################
    ##################################################################################################################################################







    #load an openstreetmap
    m = folium.Map(location=[df_MS.Lat.mean(), df_MS.Long.mean()], zoom_start=17, max_zoom=25, tiles="OpenStreetMap") # load a style of map (from OpenStreetMap, if not clarified in the command)







    ########################################### START: CREATE MARKERS, POP UP ASSOCIATED TO EACH POINT AND TO THE MAP (ITERATIVE ROUTINE)#########################################################
    #iterate over each row in the dataframe
    for i,row in df_MS.iterrows():
        #Setup the content of the popup
        #create an iframe object, which allows us to have more control over the popup appearance and content 
        # Write the html code for the popups
    ########################################### START: SET THE FORMAT AND CONTENT OF POP UP #########################################################   
        # frame for 1st level of pop up
        iframe = folium.Html(
                """
                <!DOCTYPE html>
                <html>
                
                <head>
            
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
                <link href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" rel="stylesheet"/>
            

                <style>
                <!-- This is JS code to enable multiple tabs open and close between different popup cards -->
                $('.collapse').on('hidden.bs.collapse', function () {
                    var defaultDiv = $($(this).data("parent")).data("default");
                    $('.collapse').eq(defaultDiv-1).collapse('show');
                    })
                
                <!-- This is CSS code to enable open and closing of tabs in the popup card -->
                input {
                    display: none;
                }
                label {
                    display: block;   
                    width: 250px;
                    padding: 8px 22px;
                    margin: 0 0 1px 0;
                    cursor: pointer;
                    background: #6AAB95;
                    border-radius: 3px;
                    color: #FFF;
                    transition: ease .5s;
                }

                label:hover {
                    background: #4E8774;
                }

                .content {
                    background: #E2E5F6;
                    padding: 2px 15px 2px 15px; 
                    border: 1px solid #A7A7A7;
                    margin: 0 0 1px 0;
                    border-radius: 3px;
                }

                input + label + .content {
                    display: none;
                }

                input:checked + label + .content {
                    display: block;
                }

                </style>

        
                </head>
                """
                f"""
                
                
                <body>
                
                <!-- This is Html code to enable open and closing of tabs in the popup card -->
                
                <label>{row['Tag']}</label>
                
                <input type="checkbox" id="title1" />
                <label for="title1">Prefabrication Progress</label>

                <div class="content">
                <p>
                <table>
                <tr>
                <td> Overall Quantity (Tons)</td> 
                <td> &ensp;  = &ensp; </td>
                <td>  {row['Overall_Qty']} </td> 
                </tr>
                
                <tr>
                <td> Fabrication Started (Tons)</td>
                <td> &ensp;  = &ensp; </td>
                <td>{row['Fabric_Started_Qty']}</td>
                </tr>
                
                <tr>
                <td> Fabricated (Tons)</td>
                <td>&ensp; = &ensp;</td>
                <td> {row['Fabricated_Qty']}</td>
                </tr>
                
                <tr>
                <td> Shipped (Tons)
                <td>&ensp; = &ensp; </td>
                <td>{row['Shipped_Qty']}</td> 
                </tr>
                
                <tr>
                <td> To Site (Tons)</td>
                <td>&ensp; = &ensp;</td>
                <td>{row['At_Site_Qty']}</td>
                </tr>             

                </table></p>
                </div>

                <input type="checkbox" id="title2" />
                <label for="title2">ScreenShot</label>
                <div class="content">
                <!-- reports the screenshot of the item prefabrication status and the link to 3d viewer -->
                <p>
                <a href="{"https://easyplant3d.apps.technipenergies.com/RDCG/viewer?plant=06%20-%20STEEL%20STRUCTURE&units="+row['Tag']}"  target="_blank">
                <img src="{screens_path+row['Tag']}.PNG?raw=true" title= "Click to open 3D" min widht="250" max width="250" align="center" style="border-radius: 50px;"/> 
                </a>
                </p>
                </div>
            
                </body>
            
                </html> 
                """, 
                script=True)
        
        
        # frame for 2nd level of pop up    
        iframe1 = folium.Html(row['Tag'])
        
        
        # Create the popup
        
        #Initialise the popup using the iframe
        #create the popup and pass the iframe object and dimensions of the popup
        #sticky= True keep all pop open
        
        #1st level of pop up
        popup = folium.Popup(iframe, minmax_width="100", sticky=True)
        
        #2nd level of pop up
        popup1 = folium.Popup(iframe1, max_width=200, sticky=True)
    ########################################### END: SET THE FORMAT AND CONTENT OF POP UP #########################################################
    ##################################################################################################################################################
    ########################################### START: CREATE MARKERS AND ADD TO THE MAP #########################################################
        #Add each  row to the map
        # marker draggable
    
        folium.Marker(location=[row['Lat'],row['Long']],
                    tooltip=row['Tag'],
                    icon = folium.Icon(icon='fa-building', prefix='fa'),
                    popup = popup, draggable=True).add_to(m)

        
        # marker (Circle) not draggable
        folium.Circle(location=[row['Lat'],row['Long']],radius=2, fill_color='#1f0903',tooltip=row['Tag'],
                    popup=popup1).add_to(m)
        
        
        
        
        
        
        
        # Set the popup's background  (colour, opacity,...)
        html_to_insert = "<style>.leaflet-popup-content-wrapper, .leaflet-popup.tip {background: linear-gradient(to bottom, #0099ff 0%, #ffffff 25%); opacity: 0.9; !important; }</style>"
        m.get_root().header.add_child(folium.Element(html_to_insert))
    ########################################### END: CREATE MARKERS AND ADD TO THE MAP #########################################################
    ##################################################################################################################################################    
    ########################################### END: CREATE MARKERS, POP UP ASSOCIATED TO EACH POINT AND TO THE MAP (ITERATIVE ROUTINE)#########################################################
    ##################################################################################################################################################    
        



    ########################################### START: ADD LAYER TO OSM MAP #########################################################  
    #set up of the feauters of the image to add as a layer
    img=folium.raster_layers.ImageOverlay(
    name = "sat",
    image=img1.transpose(1,2,0), #the command transpose has to be used to manage the tif format (Image Overlay should use png or jpg)
    bounds=[[51.9749, 4.0016], [51.9703, 4.0152]],
    opacity= 0.6,
    interactive=True,
    cross_origin=False,
    zindex=1, 
    )




    #add the layer to OMS
    img.add_to(m)
    #add a layer control widget
    folium.LayerControl().add_to(m)
    ########################################### END: ADD LAYER TO OSM MAP ########################################################################## 
    ##################################################################################################################################################





    ########################################### START: MAP FEATURES AND PLUGIN #########################################################  
    # add a minimap
    minimap = plugins.MiniMap(toggle_display=True, tile_layer="openstreetmap")
    m.add_child(minimap)


    # add a drawing panel
    draw = plugins.Draw(export=True)
    draw.add_to(m)


    #when open the map, the zoom is automatically set to include all the items
    sw = df_MS[['Lat', 'Long']].min().values.tolist()
    ne = df_MS[['Lat', 'Long']].max().values.tolist()
    m.fit_bounds([sw, ne]) 


    #plugin for fullscreen
    plugins.Fullscreen(
        position="bottomleft",
        title="Expand me",
        title_cancel="Exit me",
        force_separate_button=True,
    ).add_to(m)



    #QUESTA PARTE PER ESPORTARE UNO SCREENSHOT DELLA MAPPA --------- ANCORA NON FUNZIONA (non prende i layer ed i marker)
    m.get_root().header.add_child(folium.CssLink('https://pasichnykvasyl.github.io/Leaflet.BigImage/src/Leaflet.BigImage.css'))
    m.get_root().html.add_child(folium.JavascriptLink('https://pasichnykvasyl.github.io/Leaflet.BigImage/src/Leaflet.BigImage.js'))

    png_js = '''
    $(document).ready(function(){
    L.control.bigImage({position: 'topleft'}).addTo({map});
    });
    '''.replace("{map}", m.get_name())

    m.get_root().script.add_child(folium.Element(png_js))
    ########################################### END: MAP FEATURES AND PLUGIN #########################################################  
    ##################################################################################################################################################
    st_map = st_folium(m, minmax_width=1900, height=500, returned_objects=[])

    

    



def main():
    st.set_page_config(APP_TITLE)
    st.title(APP_TITLE)
    st.caption(APP_SUB_TITLE)

    display_map()

if __name__ == "__main__":
    main()   
