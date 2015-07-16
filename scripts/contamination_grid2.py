#!/usr/bin/env python

import numpy as np
import sys
from math import cos, sin, acos, sqrt

import yaml

import rospy
import tf
import geometry_msgs.msg
from std_msgs.msg import *
from nav_msgs.msg import OccupancyGrid, MapMetaData
from visualization_msgs.msg import Marker, MarkerArray

#This class converts ellipse data into an OccupancyGrid message

class Contamination:
    def __init__(self):
        self.contam_level=[]
        #self.layout = MultiArrayLayout([MultiArrayDimension(label="contam", stride=1)], 0)
        self.listener=None
        self.publisher=None
        self.contam_pub=None
        self.ogrid = OccupancyGrid()
        self.step = None
        #how fast it decreases: 1 is slowest, 0 is instantly
        self.rate = 0.8
        #list of coordinates with contamination
        self.contam={}

    def reset(self, run):
        self.contam_level = []
        self.contam={}
        self.ogrid.data = [0 for i in xrange(self.ogrid.info.width*self.ogrid.info.height)]
        with open(sys.argv[1]) as f:
            for k, v in yaml.load(f.read()).iteritems():
                #print "loaded {0}".format(v)
                self._base_contam(v["lower_left"], v["upper_right"])

    def _xy_to_cell(self, xy):
        #fit XY to nearest cell - each cell is <resolution> meters wide
        x=int(round(xy[0]/self.ogrid.info.resolution))
        y=int(round(xy[1]/self.ogrid.info.resolution))
        return y*self.ogrid.info.width+x
        #return x, y

    def _snap_to_cell(self, xy):
        return (round(xy[0]/self.ogrid.info.resolution) * self.ogrid.info.resolution,
                round(xy[1]/self.ogrid.info.resolution) * self.ogrid.info.resolution)

    def _set_map_metadata(self, metadata):
        self.ogrid.info = metadata
        self.ogrid.data = [0 for i in xrange(metadata.width*metadata.height)]
        self.step = metadata.resolution

    #add initial contamination (rectangles)
    def _base_contam(self, lower_left, upper_right):
        lower_left = self._snap_to_cell(lower_left)
        upper_right = self._snap_to_cell(upper_right)
        for x in np.arange(lower_left[0], upper_right[0], self.step):
            for y in np.arange(lower_left[1], upper_right[1], self.step):
                index = self._xy_to_cell((x, y))
                self.ogrid.data[index]=100
                self.contam[index]=(x, y)
        self.ogrid.header=Header(stamp=rospy.Time.now(),frame_id = "map")
        self.publisher.publish(self.ogrid)
        print "loaded map"

    #turn ellipse into points
    def _get_ellipse_data(self,ellipse):
        #transform map to laser to use this
        try:
            (trans,rot) = self.listener.lookupTransform('/map', '/laser', rospy.Time(0))
            center = self._snap_to_cell((ellipse.pose.position.x+trans[0], ellipse.pose.position.y+trans[1]))
            (a, b) = self._snap_to_cell((ellipse.scale.x/2, ellipse.scale.y/2))
            theta = acos(ellipse.pose.orientation.w)*2
            return center, a, b, theta
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            pass

    #return distance from point to ellipse
    def _e_dist(self, point, center, a, b, theta):
        return (pow((abs(cos(theta)*(point[0]-center[0]))+abs(sin(theta)*(point[1]-center[1])))/a, 2) +
                pow((abs(sin(theta)*(point[0]-center[0]))+abs(cos(theta)*(point[1]-center[1])))/b, 2))

    def _check_contam(self, ellipse_array):
        #check to see if they have become contaminated
        print self.contam_level
        while len(self.contam_level) < len(ellipse_array.markers):
            self.contam_level.append(-1)
        for ellipse in ellipse_array.markers:
            (center, a, b, theta)=self._get_ellipse_data(ellipse) #convert marker to points
            for k, v in self.contam.iteritems():
                distance = self._e_dist(v, center, a, b, theta) #values abnormally large?
                # if person is in area increase relative contamination
                print ellipse.id, v, center
                if distance < 1 and self.contam_level[ellipse.id]<self.ogrid.data[k]:
                    self.contam_level[ellipse.id] = self.ogrid.data[k]
            #if person is contaminated after that check, amend contamination levels in points
            if self.contam_level[ellipse.id] > -1:
                #contamination levels decrease as person distributes sickness around
                self.contam_level[ellipse.id] = self.contam_level[ellipse.id]*self.rate
                #outline square that fits ellipse and then find points within ellipse
                for x in np.arange(center[0]-a, center[0]+a, self.step):
                    for y in np.arange(center[1]-a, center[1]+a, self.step):
                        distance = self._e_dist((x, y), center, a, b, theta)
                        index = self._xy_to_cell((x, y))
                        if distance < 1 and self.ogrid.data[index]<self.contam_level[ellipse.id]: #within ellipse
                            self.ogrid.data[index]=self.contam_level[ellipse.id]
                            if index not in self.contam:
                                self.contam[index]=(x, y)
        self.ogrid.header=Header(stamp=rospy.Time.now(),frame_id = "map")
        self.publisher.publish(self.ogrid)
        #self.layout.dim.size = len(self.contam_level)
        #self.contam_pub.publish(Float32MultiArray(self.layout, self.contam_level))



    #initialize node
    def setup(self):
        rospy.init_node('contamination2', anonymous=True)
        metadata = rospy.wait_for_message("map_metadata", MapMetaData, 120)
        self._set_map_metadata(metadata)
        self.publisher=rospy.Publisher("contamination_grid", OccupancyGrid, queue_size=10, latch=True)
        #self.contam_pub=rospy.Publisher("contam", Float32MultiArray, queue_size=10)
        rospy.Subscriber("tracker_array", MarkerArray, self._check_contam)
        rospy.Subscriber("update_filter_cmd", Bool, self.reset)
        self.listener = tf.TransformListener()
        rate = rospy.Rate(10.0)
        node.reset(True)
        rospy.spin()

if __name__ == '__main__':
    node = Contamination()
    try:
        node.setup()
    except rospy.ROSInterruptException:
        pass