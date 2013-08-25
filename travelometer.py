#!/usr/bin/python

import time
from scene import *


def median(values):
  s=sorted(values)
  l=int(len(s))
  return (float(s[(l-1)/2] + s[l/2]))/2


# The following classes for dealing with buttons are taken directly
# and/or inspired by LandyQuack
class Window (Layer):
    def __init__(self, p, bounds):
        Layer.__init__(self, bounds)
        if p: p.add_layer(self)
        self.background=Color(1,1,1)
 
    def touch_began(self, touch): pass
    def touch_moved(self, touch): pass
    def touch_ended(self, touch): pass


class TextBox(Window):
    def __init__(self, p, position, text, font, size):
        Window.__init__(self, p, Rect(position.x,position.y,0,0))
        self.background = Color(0,0,0)
        self.tint = Color(1,1,1)
        self.text_img, ims = render_text(text, font_name=font, font_size=size)
        self.frame = Rect(position.x, position.y, ims.w, ims.h)
        self.image = self.text_img



class Button(Window):
    def __init__(self, p, b, callback):
        Window.__init__(self, p, b)
        #self.stroke = Color(1,1,1)
        #self.stroke_weight = 2
        self.callback = callback
        self.active = 0
        self.colorize()

    def toggle(self):
        if self.active:
            self.active = 0
        else:
            self.active = 1
        self.colorize()

    def touch_began(self, touch):
      self.callback()

    def colorize(self):
        if self.active:
            self.background = Color(1,1,1)
            self.tint = Color(0,0,0)
        else:
            self.background = Color(0,0,0)
            self.tint = Color(1,1,1)

class TextButton(Button):
    def __init__(self, p, b, callback, text, font, size):
        Button.__init__(self, p, b, callback)
        self.text_img, ims = render_text(text, font_name=font, font_size=size)
        self.image = self.text_img
        self.background = Color(0,0,0)
        self.tint = Color(1,1,1)


class TextETA(Window):
    def __init__(self, p, b, font, size, eta):
        Window.__init__(self, p, b)
        self.eta = eta
        eta_textbox = TextBox(self, Rect(0, p.size.h*0.5, p.size.w, p.size.h*0.5), '', font, size)
        tminus_textbox = TextBox(self, Rect(0, 0, p.size.w, p.size.h*0.5), '', font, size)

    def draw(self):
        now = time.time()
        remaining_time = eta - now
        eta_textbox.image = text_render(time.strftime("ETA: %H:%M:%S %Z",time.localtime(eta)))
        if remaining_time > 0:
            tminus_textbox.image = text_render(time.strftime("T minus %H:%M:%S",remaining_time))
        else:
            tminus_textbox.image = text_render(time.strftime("T plus %H:%M:%S",-remaining_time))
 
        


class TravelLayer(Window):
    def __init__(self, p, tripobj):
        Window.__init__(self, p, Rect(0, 0, p.frame.w, p.frame.h*0.8))
        self.thistrip = tripobj
        self.background = Color(0,0,0)
        self.tint = Color(1,1,1)
        TextBox(self, Rect(self.frame.w*0.05, self.frame.h*0.9, self.frame.w*0.4,
          self.frame.h*0.05), 'Trip', 'Futura', 20)
        trip_texteta = TextETA(self, Rect(self.frame.w*0.1, self.frame.h*0.8,
          self.frame.w*0.9, self.frame.h*0.1), 'Futura', 30, tripobj.estimated_finish())
        




class MedianIterator(object):
  "an iteration to the median segment solution"
  def __init__(self, segmentlist):
    self.numsegs = max(map(lambda x:x[1],segmentlist))
    self.singlesegments = [[] for i in range(self.numsegs+1)]
    self.multisegments = []
    for seg in segmentlist:
      if (seg[1]==seg[0]):
	self.singlesegments[seg[0]].append(seg[2])
      else:
	self.multisegments.append(seg)
    # initial guess: single segments
    self.mediantimes = [[] for i in range(self.numsegs+1)]
    for segnum in range(len(self.singlesegments)):
      self.mediantimes[segnum] = median(self.singlesegments[segnum])

  def add_segment(self, seg):
    if (seg[1]==seg[0]):
      self.singlesegments[seg[0]].append(seg[2])
    else:
      self.multisegments.append(seg)


  def results(self):
    return self.mediantimes

  def iterate(self):
    "do an iteration of adding in longer segments"
    initial_medians = self.mediantimes
    this_segtimes = self.singlesegments
    for multiseg in self.multisegments:
      # break total time up according to current median times
      npieces = multiseg[1]-multiseg[0]+1
      median_full = float(sum(self.mediantimes[multiseg[0]:multiseg[1]+1]))
      for pieceofmulti in map(lambda x:x+multiseg[0], range(npieces)):
	this_segtimes[pieceofmulti].append(multiseg[2]*self.mediantimes[pieceofmulti]/median_full)

    for segnum in range(len(this_segtimes)):
      self.mediantimes[segnum] = median(this_segtimes[segnum])

    # check for convergence
    return initial_medians==self.mediantimes

  def iterate_to_convergence(self, maxiterations=10):
    #print "Initial guess:",self.mediantimes
    for i in range(maxiterations):
      convergedp = self.iterate()
      #print " Iteration",i,":",self.mediantimes
      if convergedp:
        break





class TravelometerError(Exception): pass

class InvalidInputError(TravelometerError):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class EndOfTripError(TravelometerError):
  def __init__(self): pass



class Trip(object):
  def __init__(self, medianiter, direction):
    self.mediantimes = medianiter
    self.numpoints = self.mediantimes.numsegs+1
    # direction is 'E' (to WV) or 'W' (to AL)
    if direction=='E':
      self.direction=1
      self.lastmilestone=0
    elif direction=='W':
      self.direction=-1
      self.lastmilestone=self.numpoints
    else:
      raise InvalidInputError(direction)
    self.nextmilestone = self.lastmilestone+self.direction
   
    # set the clock running 
    self.lastclock=time.time()
    self.segs = []

  def skip_milestone(self):
    self.nextmilestone += self.direction
    if (self.nextmilestone==-1) or (self.nextmilestone==self.numpoints+1):
      raise EndOfTripError()

  def checkpoint(self):
    # add a new segment to the list, update milestones/clocks, and recalibrate
    clockcheck = time.time()
    segmenttime = (clockcheck-self.lastclock)/60.0
    if (self.direction==1):
      newseg = [self.lastmilestone, self.nextmilestone-1, segmenttime]
    else:
      newseg = [self.nextmilestone, self.lastmilestone-1, segmenttime]
    self.segs.append(newseg)
    self.lastclock = clockcheck
    self.lastmilestone = self.nextmilestone
    self.nextmilestone = self.lastmilestone+self.direction
    if (self.nextmilestone==-1) or (self.nextmilestone==self.numpoints+1):
      raise EndOfTripError()
    self.mediantimes.add_segment(newseg)
    self.mediantimes.iterate_to_convergence()
 
  def estimated_next_milestone(self, milestone=None):
    if milestone is None:
      milestone=self.nextmilestone
    if (self.direction==1):
      time_remaining = sum(self.mediantimes.results()[self.lastmilestone:milestone])
    else:
      time_remaining = sum(self.mediantimes.results()[milestone:self.lastmilestone])
    clock_at_end = self.lastclock + 60.0*time_remaining
    #localtime_at_end = time.localtime(clock_at_end)
    #return (localtime_at_end, clock_at_end, time_remaining)
    return clock_at_end

  def estimated_finish(self):
    if (self.direction==1):
      endpoint = self.numpoints
    else:
      endpoint = 0
    return self.estimated_next_milestone(endpoint)

  def get_last_checkpoint(self):
    return (self.lastmilestone, time.localtime(self.lastclock))

  def get_next_milestone(self):
    return self.nextmilestone  

  def get_segments(self):
    return self.segs


class Travelometer(Scene):
    def setup(self):
        # root layer
        p = self.root_layer = Layer(self.bounds)

        # define segments and Google Maps travel times
        self.segment_names = ['Forest Trail Apartments (Northport AL)',
          'I-59/I-459 interchange (Birmingham AL)',
          'I-59/I-759 interchange (Gadsden AL)', 
          'I-59/US-11 interchange (Fort Payne AL)',
          'I-75 exit 5 (Chattanooga TN)',
          'I-75 exit 27 (Cleveland TN)',
          'I-40/I-81 interchange (Dandridge TN)',
          'I-81 exit 7 (Bristol VA)',
          'I-81 exit 70 (Wytheville VA)',
          'I-77/US-460 interchange (Princeton WV)',
          'VA/WV line (Rich Creek VA)',
          'US-60/WV-92 intersection (White Sulpher Springs WV)',
          'WV-92/39 intersection (Minnehaha Springs WV)',
          'Rabbit Patch (Arbovale WV)']

        self.begin_label = 'AL'
        self.end_label = 'WV'
        self.introtext = 'Press an arrow to begin trip.'

        self.segment_googletimes = [68, 37, 35, 54, 18, 97, 71, 56, 37, 21, 63, 35, 35]

        self.trip_segments = []
        # turn google ones into form that MedianIterator takes for initialization
        for googleseg in range(len(self.segment_googletimes)):
          self.trip_segments.append([googleseg, googleseg, self.segment_googletimes[googleseg]])

        # read in previous trips if available and add them too
        self.tripfilename = 'travelometerdata.dat'
        try:
          tripfile = open(self.tripfilename, 'r')
          triplines = tripfile.readlines()
          tripfile.close()
          for tripline in triplines:
            beginseg, endseg, segmin = tripline.split(' ')
            self.trip_segments.append([int(beginseg), int(endseg), float(segmin)])
        except IOError:
          pass

        # create the MedianIterator
        self.estimatedtimes = MedianIterator(self.trip_segments)
        # iterate to convergence
        self.estimatedtimes.iterate_to_convergence()
        
        self.travel = None

        # create UI elements
        screensize = self.size
        TextBox(p, Rect(screensize.w*0.1, screensize.h*0.83, screensize.w*0.2,
            screensize.h*0.08), self.begin_label, 'Futura', 100)
        TextBox(p, Rect(screensize.w*0.72, screensize.h*0.83, screensize.w*0.2,
            screensize.h*0.08), self.end_label, 'Futura', 100)
        self.forwardarrowbutton = Button(p, Rect(screensize.w*0.42, screensize.h*0.90,
            screensize.w*0.16, screensize.h*0.06), self.forwardtrip_buttonpress)
        self.forwardarrowbutton.image = 'Typicons48_Right'
        self.backarrowbutton = Button(p, Rect(screensize.w*0.42, screensize.h*0.84,
            screensize.w*0.16, screensize.h*0.06), self.backwardtrip_buttonpress)
        self.backarrowbutton.image = 'Typicons48_Left'

        self.introlayer = TextBox(p, Rect(screensize.w*0.1, screensize.h*0.5, screensize.w*0.2,
            screensize.h*0.08), self.introtext, 'Futura', 50)
 

    def forwardtrip_buttonpress(self):
       if self.travel is None:
          self.travel = Trip(self.estimatedtimes, 'E')
          self.forwardarrowbutton.toggle()
          self.introlayer.remove_layer()
          self.travel_layer = TravelLayer(self.root_layer, self.travel)

    def backwardtrip_buttonpress(self):
      if self.travel is None:
          self.travel = Trip(self.estimatedtimes, 'W')
          self.backarrowbutton.toggle()
          self.introlayer.remove_layer()
          self.travel_layer = TravelLayer(self.root_layer, self.travel)
        

    def draw(self):
        self.root_layer.update(self.dt)
        self.root_layer.draw()




## run a trip
#directionletter = raw_input("Direction: [E]astbound (to WV) or [W]estbound (to AL)? ").upper()
#try:
#  travel = Trip(estimatedtimes, directionletter)
#  while True:
#    lastcheckpoint = travel.get_last_checkpoint()
#    nextcheckpoint = travel.get_next_milestone()
#    next_time = travel.estimated_next_milestone()
#    last_time = travel.estimated_finish()
#    print "Last checkpoint: "+segment_names[lastcheckpoint[0]]+" at "+time.strftime("%H:%M %Z",lastcheckpoint[1])
#    print "Next checkpoint: "+segment_names[nextcheckpoint]+" at "+time.strftime("%H:%M %Z",next_time[0])
#    print "Remaining minutes: "+str(last_time[2])
#    print "ETA: "+time.strftime("%H:%M %Z",last_time[0])
#    actionletter = raw_input("[C]heckpoint or [S]kip? ").upper()
#    if (actionletter=='C'):
#      travel.checkpoint()
#    elif (actionletter=='S'):
#      travel.skip_milestone()
#    else:
#      raise InvalidInputError(actionletter)
#except EndOfTripError: pass
#
## write out new trip before quitting
#tripfile=open(tripfilename, 'a')
#for seg in travel.get_segments():
#  tripfile.write(str(seg[0])+" "+str(seg[1])+" "+str(seg[2])+"\n")
#tripfile.close()



run(Travelometer(), PORTRAIT)

