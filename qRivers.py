# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qRivers
                                 A QGIS plugin
 Toolset to calculate river statistics
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-04-06
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Evan Greenberg
        email                : egreenberg@ucsb.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QAbstractItemView, QListView
from qgis.core import QgsProject, Qgis, QgsRasterLayer, QgsVectorLayer

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .qRivers_dialog import treeDialog 
from .qRivers_dialog import maskDialog 
from .qRivers_dialog import centerlineDialog 
from .qRivers_dialog import widthDialog 
from .qRivers_dialog import graphDialog 
from .qRivers_dialog import migrationDialog 

import os.path
import joblib
import pickle
import rasterio

# QRiversCode
from qRiversCode import Classification
from qRiversCode import Centerline 
from qRiversCode import Width 
from qRiversCode import GraphSort
from qRiversCode import Migration 


class qRivers:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'qRivers_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&qRivers')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('qRivers', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/qRivers/icon.png'
#        icon_path = ':/plugins/qRivers/qRTree_icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create Tree'),
            callback=self.Tree,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Generate Mask - Batch'),
            callback=self.Mask,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Generate Centerline - Batch'),
            callback=self.findCenterline,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Find Width - Batch'),
            callback=self.findWidth,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Generate Graph - Batch'),
            callback=self.Graph,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Calculate Migration'),
            callback=self.Migration,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&qRivers'),
                action)
            self.iface.removeToolBarIcon(action)


    def select_output_file(self):
        filename, _filter = QFileDialog.getSaveFileName(
            self.dlg, 
            "Select   output file ","", 
            f'*.{self.ext}'
        )
        self.dlg.OutputFile.setText(filename)

    def select_input_file(self):
        filename, _filter = QFileDialog.getOpenFileName(
            self.dlg, 
            "Select input file "
        )
        self.dlg.InputFile.setText(filename)

    def select_poly_file(self):
        filename, _filter = QFileDialog.getSaveFileName(
            self.dlg, 
            "Select poly output file ",""
        )
        self.dlg.outputPoly.setText(filename)


    def select_output_root(self):
        filename = QFileDialog.getExistingDirectory(
            self.dlg
        )
        self.dlg.outputRoot.setText(filename)

    def select_clf_file(self):
        filename, _filter = QFileDialog.getOpenFileName(
            self.dlg,
            "Select clf file"
        )
        self.dlg.clfFile.setText(filename)

    def select_file(self, sfile):
        filename, _filter = QFileDialog.getOpenFileName(
            self.dlg,
            "Select clf file"
        )
        sfile.setText(filename)

    def Tree(self):
        """Run method that performs all the real work"""
        self.first_start = False
        self.dlg = treeDialog()
        self.ext = 'pkl'
        self.dlg.Browse.clicked.connect(self.select_output_file)

        # Fetch the currently loaded layers
        active_layers = QgsProject.instance().layerTreeRoot().children()
        # Layer options
        input_layers = {
                'raster': self.dlg.InputRaster,
                'land': self.dlg.LandPoints,
                'water': self.dlg.WaterPoints,
        }
        for name, input_layer in input_layers.items():
            # Clear the contents of the comboBox from previous runs
            input_layer.clear()
            # Populate the comboBox with names of all the loaded layers
            input_layer.addItems(
                [layer.name() for layer in active_layers]
            )

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            rasterIndex = input_layers['raster'].currentIndex()
            rasterLayer = active_layers[rasterIndex].layer()

            waterIndex = input_layers['water'].currentIndex()
            waterLayer = active_layers[waterIndex].layer()

            landIndex = input_layers['land'].currentIndex()
            landLayer = active_layers[landIndex].layer()

            clf = Classification.generateTreeQ(
                rasterLayer,
                waterLayer,
                landLayer,
            )

            # Do something useful here - delete the line containing pass and
            filename = self.dlg.OutputFile.text()
            with open(filename, 'w') as output_file:
                joblib.dump(clf, filename, compress=9)

            self.iface.messageBar().pushMessage(
              "Success", "Output file written at " + filename,
              level=Qgis.Success, duration=3)

    def Mask(self):
        """Run method that performs all the real work"""
        self.dlg = maskDialog()
        self.ext = 'tif'
        self.dlg.OutputBrowse.clicked.connect(self.select_output_root)
        self.dlg.clfBrowse.clicked.connect(self.select_clf_file)

        self.dlg.outputRoot.clear()
        self.dlg.clfFile.clear()


       # Trying to set up the listWidgetView
        self.dlg.listWidget.setEditTriggers(
            QAbstractItemView.DoubleClicked
            |QAbstractItemView.EditKeyPressed
        )
        self.dlg.listWidget.setSelectionMode(
            QAbstractItemView.MultiSelection
        )
        self.dlg.listWidget.setViewMode(QListView.ListMode)

        # Load the layers in the listWidget
        layers = QgsProject.instance().layerTreeRoot().children()
        # Clear the contents of the comboBox from previous runs
        self.dlg.listWidget.clear()
        # Populate the listWidget with all the polygon layer present in the TOC
        self.dlg.listWidget.addItems([layer.name() for layer in layers])

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            # Load the classifier
            with open(self.dlg.clfFile.text(), 'rb') as fid:
                clf = joblib.load(fid)

            # Get all the paths from the selected files
            selectedLayers = self.dlg.listWidget.selectedItems()
            for layer in selectedLayers:
                layerName = layer.text()
                rasterLayer = QgsProject.instance().mapLayersByName(layerName)[0]
                # Log the file
                self.iface.messageBar().pushMessage(
                    rasterLayer.source(),
                    level=Qgis.Success, 
                    duration=3
                )

                # Get Prediction
                ds = rasterio.open(rasterLayer.source())
                prediction = Classification.predictPixelsQ(
                    ds,
                    clf
                )

                # If root/mask doesn't exist, create
                root = os.path.join(
                    self.dlg.outputRoot.text(),
                    'mask'
                )
                if not os.path.exists(root):
                    os.makedirs(root)

                # Get Filename 
                name = layerName.split('_')
                name[-1] = 'mask'
                name = '_'.join(name)
                opath = os.path.join(
                    root,
                    name
                )

                # Save file
                meta = ds.meta.copy()
                meta.update({'dtype': rasterio.int8, 'count': 1})
                with rasterio.open(opath, "w", **meta) as dest:
                    dest.write(prediction.astype(rasterio.int8), 1)

                # Add layer to map
                checked = self.dlg.checkBox.isChecked()
                if checked:
                    rlayer = QgsRasterLayer(opath, name)
                    QgsProject.instance().addMapLayer(rlayer)


    def findCenterline(self):
        """Run method that performs all the real work"""

        self.dlg = centerlineDialog()
        self.ext = 'tif'
        self.dlg.outputBrowse.clicked.connect(
            self.select_output_root
        )

        self.dlg.outputRoot.clear()

        # Populate orientation options
        self.dlg.orientation.clear()
        orientations = ['EW', 'NS']
        self.dlg.orientation.addItems([o for o in orientations])

       # Trying to set up the listWidgetView
        self.dlg.listWidget.setEditTriggers(
            QAbstractItemView.DoubleClicked
            |QAbstractItemView.EditKeyPressed
        )
        self.dlg.listWidget.setSelectionMode(
            QAbstractItemView.MultiSelection
        )
        self.dlg.listWidget.setViewMode(QListView.ListMode)

        # Load the layers in the listWidget
        layers = QgsProject.instance().layerTreeRoot().children()
        # Clear the contents of the comboBox from previous runs
        self.dlg.listWidget.clear()
        # Populate the listWidget with all the polygon layer present in the TOC
        self.dlg.listWidget.addItems([layer.name() for layer in layers])

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            selectedLayers = self.dlg.listWidget.selectedItems()
            for layer in selectedLayers:
                layerName = layer.text()
                rasterLayer = QgsProject.instance().mapLayersByName(layerName)[0]
                # Log the file
                self.iface.messageBar().pushMessage(
                    rasterLayer.source(),
                    level=Qgis.Success, 
                    duration=3
                )

                es = str(self.dlg.orientation.currentText())

                # Open the image
                ds = rasterio.open(rasterLayer.source())
                image = ds.read()
                image = image[0, :, :]

                image = Centerline.getLargest(image)
                image = Centerline.fillHoles(image)
                raw_centerline = Centerline.getCenterline(image)

                # Find threshold for continuous centerline
                thresh = 100
                close_points = False 
                while not close_points:
                    print('Trying threshold: ', thresh)

                    self.iface.messageBar().pushMessage(
                        'Trying threshold: ' + str(thresh),
                        level=Qgis.Success, 
                        duration=3
                    )

                    centerline, river_endpoints = Centerline.cleanCenterline(
                        raw_centerline, 
                        es, 
                        thresh 
                    )
                    centerline = Centerline.getLargest(centerline)

                    close_points = Centerline.getCenterlineExtent(
                        centerline, 
                        river_endpoints,
                        maxdistance=50
                    )
                    thresh -= 10

                # Use the found threshold
                thresh = thresh + 10

                self.iface.messageBar().pushMessage(
                    'Using threshold: ' + str(thresh),
                    level=Qgis.Success, 
                    duration=3
                )

                centerline, river_endpoints = Centerline.cleanCenterline(
                    raw_centerline, 
                    es, 
                    thresh
                )
                centerline = Centerline.getLargest(centerline)

                # If root/mask doesn't exist, create
                root = os.path.join(
                    self.dlg.outputRoot.text(),
                    'centerline'
                )
                if not os.path.exists(root):
                    os.makedirs(root)

                # Get Filename 
                name = layerName.split('_')
                name[-1] = 'centerline'
                name = '_'.join(name)
                opath = os.path.join(
                    root,
                    name
                )

                # Save file
                meta = ds.meta.copy()
                meta.update({'dtype': rasterio.int8, 'count': 1})
                with rasterio.open(opath, "w", **meta) as dest:
                    dest.write(centerline.astype(rasterio.int8), 1)

                # Add layer to map
                checked = self.dlg.checkBox.isChecked()
                if checked:
                    rlayer = QgsRasterLayer(opath, name)
                    QgsProject.instance().addMapLayer(rlayer)


    def findWidth(self):
        """Run method that performs all the real work"""

        self.ext = 'csv'
        self.dlg = widthDialog()
        self.dlg.widthBrowse.clicked.connect(self.select_output_file)

        self.dlg.polyBrowse.clicked.connect(self.select_poly_file)

        # Fetch the currently loaded layers
        layers = QgsProject.instance().layerTreeRoot().children()
        # Populate Centerline + Mask layers
        self.dlg.centerlineLayer.clear()
        self.dlg.maskLayer.clear()

        self.dlg.centerlineLayer.addItems(
            [layer.name() for layer in layers]
        )
        self.dlg.maskLayer.addItems(
            [layer.name() for layer in layers]
        )

        # Populate the SpinBox
        self.dlg.stepBox.setValue(5)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Get setep
            step = self.dlg.stepBox.value()

            # Get paths
            centerlineIndex = self.dlg.centerlineLayer.currentIndex()
            centerlineLayer = layers[centerlineIndex].layer()

            maskIndex = self.dlg.maskLayer.currentIndex()
            maskLayer = layers[maskIndex].layer()

            self.iface.messageBar().pushMessage(
              str(centerlineLayer.source()),
              level=Qgis.Success, duration=3)

            self.iface.messageBar().pushMessage(
              str(maskLayer.source()),
              level=Qgis.Success, duration=3)

            self.iface.messageBar().pushMessage(
              str(step),
              level=Qgis.Success, duration=3)

            # Get width and river shape
            width_df, river_polygon = Width.getWidth(
                centerlineLayer.source(),
                maskLayer.source(),
                step
            )

            # Saving Width File
            filename = self.dlg.OutputFile.text()
            width_df.to_csv(filename)

            # Saving polygon file
            pname = self.dlg.outputPoly.text()
            with open(pname, "wb") as poly_file:
                pickle.dump(river_polygon, poly_file, pickle.HIGHEST_PROTOCOL)

            # Add to map
            checked = self.dlg.addMap.isChecked()
            if checked:
                delim = ','
                xfield = 'x'
                yfield = 'y'
                uri = f'file:///{filename}?d?delimiter={delim}&xField={xfield}&yField={yfield}'
                layer_csv = QgsVectorLayer(
                    uri, 
                    filename.split('/')[-1], 
                    'delimitedtext'
                )
                QgsProject.instance().addMapLayer(layer_csv)


    def Graph(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.first_start = False
        self.ext = ''
        self.dlg = graphDialog()
        self.dlg.csvBrowse.clicked.connect(self.select_input_file)
        self.dlg.Browse.clicked.connect(self.select_output_file)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Get Width DF 
            input_fp = self.dlg.InputFile.text()

            self.iface.messageBar().pushMessage(
                f'Finding Graph: {input_fp}',
                level=Qgis.Success, 
                duration=3
            )

            # Find Graph
            G = GraphSort.getGraph(
                input_fp, 
                xcol='rowi', 
                ycol='coli'
            )

            # Write graph
            opath = self.dlg.OutputFile.text()
            GraphSort.saveGraph(G, opath)

            self.iface.messageBar().pushMessage(
                'Wrote Graph',
                level=Qgis.Success, 
                duration=3
            )


    def Migration(self):
        """
        Inputs:
            polyfile1:          poly 
            centerlinefile1:    csv
            graph1:             graph 

            polyfile2:          poly 
            centerlinefile2:    csv
            graph2:             graph
            image2:             tif

            Cutoff locations:   shp
            need to go from shapefile to array of points
        """

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.dlg = migrationDialog()

        # Polygons
        self.dlg.polygon1Browse.clicked.connect(
            lambda: self.select_file(self.dlg.Polygon1)
        )
        self.dlg.polygon2Browse.clicked.connect(
            lambda: self.select_file(self.dlg.Polygon2)
        )

        # Centerlines
        self.dlg.centerline1Browse.clicked.connect(
            lambda: self.select_file(self.dlg.Centerline1)
        )
        self.dlg.centerline2Browse.clicked.connect(
            lambda: self.select_file(self.dlg.Centerline2)
        )

        # Graphs
        self.dlg.graph1Browse.clicked.connect(
            lambda: self.select_file(self.dlg.Graph1)
        )
        self.dlg.graph2Browse.clicked.connect(
            lambda: self.select_file(self.dlg.Graph2)
        )

        self.ext = 'csv'
        self.dlg.Browse.clicked.connect(self.select_output_file)

        # Fetch the currently loaded layers
        layers = QgsProject.instance().layerTreeRoot().children()
        # Clear the contents of the comboBox from previous runs
        self.dlg.CutoffLayer.clear()
        # Populate the comboBox with names of all the loaded layers
        self.dlg.CutoffLayer.addItems([layer.name() for layer in layers])

        # Set date
        self.dlg.Date1.setDisplayFormat('yyyy-MM-dd')
        self.dlg.Date1.setCalendarPopup(True)
        self.dlg.Date2.setDisplayFormat('yyyy-MM-dd')
        self.dlg.Date2.setCalendarPopup(True)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Get Time 
            time1 = self.dlg.Date1.date().toString(Qt.ISODate)
            time2 = self.dlg.Date2.date().toString(Qt.ISODate)

            # Polypaths paths
            polypath1 = self.dlg.Polygon1.text()
            polypath2 = self.dlg.Polygon2.text()

            # Centerline paths 
            clpath1 = self.dlg.Centerline1.text()
            clpath2 = self.dlg.Centerline2.text()

            # Graph paths 
            graphpath1 = self.dlg.Graph1.text()
            graphpath2 = self.dlg.Graph2.text()

            # Get cutoff shapefile
            cutoffIndex = self.dlg.CutoffLayer.currentIndex()
            cutoffLayer = layers[cutoffIndex].layer()
            cutoffpath = cutoffLayer.source()

            # Cutoff points and get row, col of cutoff coords
            cutoff = Migration.getCutoffPoints(
                cutoffpath, 
                graphpath2,
                clpath2,
                
            )

            # Calculate Migration
            cl2_migration = Migration.qMigration(
                time1, polypath1, clpath1, graphpath1,
                time2, polypath2, clpath2, graphpath2,
                cutoff 
            )

            # Saving Migration File
            filename = self.dlg.OutputFile.text()
            cl2_migration.to_csv(filename)

            # Add to map if checked 
            checked = self.dlg.addMap.isChecked()
            if checked:
                delim = ','
                xfield = 'x'
                yfield = 'y'
                uri = f'file:///{filename}?d?delimiter={delim}&xField={xfield}&yField={yfield}'
                layer_csv = QgsVectorLayer(
                    uri, 
                    filename.split('/')[-1], 
                    'delimitedtext'
                )
                QgsProject.instance().addMapLayer(layer_csv)
