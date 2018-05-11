import sys
from PyQt4 import QtGui, QtCore
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from bagfile_io.bagfile_reader import bagfile_reader,write_to_bagfile
from cv_bridge import CvBridge
import numpy as np
from plot_generator import plotResult_colorbars,get_color_map
from matplotlib.widgets import RectangleSelector
from copy import deepcopy
from std_msgs.msg import String
import rosbag

class Window(QtGui.QDialog):
    topic_types = ["WrenchStamped"]

    def __init__(self, parent=None,inbag = "./data/cup_grasp1.bag",
                 outbag = "./data/cup_grasp1_out.bag",
                 image_topic = "/usb_cam_node/image_raw",
                 signal_topic = "/ftmini40",labels_topic = "/labels"):
        super(Window, self).__init__(parent)

        self.image_topic = image_topic
        self.signal_topic = signal_topic
        self.inbag = inbag
        self.outbag = outbag
        self.labels_topic = labels_topic

        # creating the figure instances
        self.figure_image = Figure()
        self.figure_image.set_facecolor('white')
        self.figure_signal = Figure()
        self.figure_signal.set_facecolor('white')
        self.figure_labels = Figure()
        self.figure_labels.set_facecolor('white')
        self.figure_timeline = Figure()
        self.figure_timeline.set_facecolor('white')

        # creating the canvas and widgets
        self.canvas = FigureCanvas(self.figure_image)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.bagfilepath = QtGui.QLineEdit(self.canvas)
        self.bagfileoutpath = QtGui.QLineEdit(self.canvas)
        self.imagetopic = QtGui.QComboBox(self.canvas)
        self.signaltopic = QtGui.QComboBox(self.canvas)
        self.topictypes = QtGui.QComboBox(self.canvas)
        self.labelsimage = FigureCanvas(self.figure_labels)
        self.currentlabel = QtGui.QLineEdit(self.canvas)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self.canvas)
        self.signalplot = FigureCanvas(self.figure_signal)
        self.timeline = FigureCanvas(self.figure_timeline)

        self.button_update = QtGui.QPushButton('update')
        self.button_update.clicked.connect(self.update_labels)

        self.button_create = QtGui.QPushButton('create out bag file')
        self.button_create.clicked.connect(self.create_button_callback)

        # creating the layout
        layout = QtGui.QGridLayout()
        layout.addWidget(self.bagfilepath, 0, 0,1,2)
        layout.addWidget(self.bagfileoutpath, 1, 0,1,2)
        layout.addWidget(self.imagetopic, 2, 0,1,2)
        layout.addWidget(self.signaltopic, 3, 0)
        layout.addWidget(self.topictypes, 3, 1)
        layout.addWidget(self.canvas, 4, 0)
        layout.addWidget(self.toolbar, 5, 0)
        layout.addWidget(self.currentlabel, 5, 1)
        layout.addWidget(self.labelsimage, 4, 1)
        layout.addWidget(self.slider, 6, 0,1,2)
        layout.addWidget(self.signalplot, 7, 0,1,2)
        # layout.addWidget(self.timeline, 8, 0,1,2)
        layout.addWidget(self.button_update, 8, 0)
        layout.addWidget(self.button_create, 8, 1)
        self.layout = layout
        self.setLayout(self.layout)

        # initial setup done

        self.bf = bagfile_reader(inbag)
        # if self.bf is None: raise ValueError('Bag file cannot be read!')

        self.images, self.image_t = self.bf.get_topic_msgs(self.image_topic)
        self.signal, self.signal_t= self.bf.get_topic_msgs(self.signal_topic)
        self.topics = self.bf.topics

        if labels_topic not in self.topics:
            print "creating labels signal for bag file"
            self.labels_t = deepcopy(self.signal_t)
            # Note labels can only be a max of 100 characters
            self.labels = np.array([""]*len(self.labels_t)).astype('a100')
        else:
            self.labels,self.labels_t = self.bf.get_topic_msgs(labels_topic)
            self.labels = [label.data for label in self.labels]
        self.label_names = list(set(self.labels))
        print self.label_names

        # method sets the widgets up such as populating combo boxes and filling in text
        self.setup_widgets()


    def setup_widgets(self):
        # I'm hard coding a lot of this
        self.bagfilepath.setText(QtCore.QString(self.inbag))
        self.bagfilepath.setToolTip(QtCore.QString("the input bag file"))



        self.bagfileoutpath.setText(QtCore.QString(self.outbag))
        self.bagfileoutpath.setToolTip(QtCore.QString("the output bag file with the label names"))


        self.signaltopic.setToolTip(QtCore.QString("signal topic"))
        self.imagetopic.setToolTip(QtCore.QString("image topic"))

        for item in self.topics:
            qstring = QtCore.QString(item)
            self.imagetopic.addItem(qstring)

        for item in self.topics:
            qstring = QtCore.QString(item)
            self.signaltopic.addItem(qstring)

        for item in self.topic_types:
            qstring = QtCore.QString(item)
            self.topictypes.addItem(qstring)

        #plotting
        self.setup_plot()

        # slider setup
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.signal_t))

        # setting up figures
        self.setup_image()
        self.setup_plot()
        self.canvas.draw()
        self.update_labels_plot()

        # setting up callbacks
        # self.bagfilepath.textChanged.connect(self.update_inbag_file)

        self.slider.valueChanged.connect(self.slider_callback)

    def line_select_callback(self, eclick, erelease):
        """eclick and erelease are the press and release events"""
        self.x1, self.y1 = eclick.xdata, eclick.ydata
        self.x2, self.y2 = erelease.xdata, erelease.ydata
        self.extents = self.RS.extents

    def update_labels_plot(self):
        #TODO update the labels plot here
        num_labels = len(self.label_names)
        color_map = get_color_map(self.label_names)
        self.figure_labels.clf()
        for ii,label in enumerate(self.label_names):
            current_ax = self.figure_labels.add_subplot(num_labels,1,ii + 1)
            current_ax.imshow([[color_map[ii]]])
            current_ax.text(0,0,str(label),ha = "center")
            current_ax.axis("Off")
        self.labelsimage.draw()

    def setup_plot(self):
        self.ax = self.figure_signal.add_subplot(2,1,1)
        self.vl = self.ax.axvline(self.signal_t[0], color='r', linewidth=3)
        '''Hard coded for WrenchStamped change later'''
        # TODO functionality to change topic type
        fx = np.array([element.wrench.force.x for element in self.signal])
        fy = np.array([element.wrench.force.y for element in self.signal])
        fz = np.array([element.wrench.force.z for element in self.signal])

        tx = [element.wrench.torque.x for element in self.signal]
        ty = [element.wrench.torque.y for element in self.signal]
        tz = [element.wrench.torque.z for element in self.signal]

        t = np.array(self.signal_t)
        self.ax.plot(t,fx)
        self.ax.plot(t,fy)
        self.ax.plot(t,fz)
        self.ax.axis("Off")
        # self.ax.plot(t,tx,'k')
        # self.ax.plot(t,ty,'k')
        # self.ax.plot(t,tz,'k')

        self.RS = RectangleSelector(self.ax, self.line_select_callback,
                                               drawtype='box', useblit=True,
                                               button=[1, 3],  # don't use middle button
                                               interactive=True)

        self.ax_timeline = self.figure_signal.add_subplot(2,1,2)
        self.vl_timeline = self.ax_timeline.axvline(self.signal_t[0], color='r', linewidth=3)

        self.label_names = list(set(self.labels))

        plotResult_colorbars(self.labels,
                             self.labels_t, ax=self.ax_timeline,labelNames=self.label_names)


        self.ax.set_xlim([t[0], t[-1]])
        self.ax_timeline.set_xlim([t[0], t[-1]])

        self.signalplot.draw()


    def update_inbag_file(self,text):
        print "text changed" + text
        #TODO
        pass

    def update_outbag_file(self,text):
        print "text changed" + text
        pass

    def slider_callback(self,value):
        self.vl.set_xdata(self.signal_t[value])
        self.vl_timeline.set_xdata(self.signal_t[value])
        if len(self.image_t) == 0:
            return
        else:
            image_id = np.argmax(self.image_t > self.signal_t[value])
            imdata = self.bridge.imgmsg_to_cv2(self.images[image_id], "rgb8")
            self.im_ax.set_data(imdata)
            self.canvas.draw()
            self.signalplot.draw()

    def setup_image(self):
        ''' updates the image'''

        # create an axis
        ax = self.figure_image.add_subplot(111)
        # discards the old graph
        ax.clear()
        self.bridge = CvBridge()
        if len(self.image_t) == 0:
            return
        else:
            img = self.bridge.imgmsg_to_cv2(self.images[0], "rgb8")
            self.im_ax = ax.imshow(img)
            ax.axis("Off")

        # refresh canvas
        self.canvas.draw()

    def update_labels(self):
        x_min = float(self.extents[0])
        x_max = float(self.extents[1])
        # print str((self.currentlabel.text().toAscii()))

        x_min_id = int(np.argmax(self.labels_t > x_min))
        x_max_id = int(np.argmax(self.labels_t > x_max))

        for ii in range(x_min_id,x_max_id):
            self.labels[ii] = str(self.currentlabel.text().toAscii())

        self.label_names = list(set(self.labels))
        self.update_labels_plot()
        plotResult_colorbars(self.labels,
                             self.labels_t, ax=self.ax_timeline,labelNames=self.label_names)
        self.ax_timeline.set_xlim([self.signal_t[0], self.signal_t[-1]])


        self.signalplot.draw()

    def create_button_callback(self):
        string_message_list = []
        for label in self.labels:

            message = String()
            message.data = label
            string_message_list.append(message)

        self.outbag = self.bagfileoutpath.text()
        print "Writing! Please be patient"
        with rosbag.Bag(self.outbag, 'w') as outbag:
            for topic, msg, t in rosbag.Bag(self.inbag).read_messages():
                # This also replaces tf timestamps under the assumption
                # that all transforms in the message share the same timestamp
                if topic == self.labels_topic:
                    pass
                else:
                    outbag.write(topic, msg, msg.header.stamp if msg._has_header else t)

        write_to_bagfile(self.outbag,self.labels_topic,string_message_list,self.labels_t,'a',createbackup=True)
        print "Done Writing: ", self.outbag, "!"


if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)

    main = Window()
    main.show()

    sys.exit(app.exec_())