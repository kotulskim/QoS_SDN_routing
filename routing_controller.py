# The program implements a simple controller for a network with 6 hosts and 5 switches.

# The switches are connected in a diamond topology (without vertical links):

#    - 3 hosts are connected to the left (s1) and 3 to the right (s5) edge of the diamond.



from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.packet_base import packet_base
from pox.lib.packet.packet_utils import *
import pox.lib.packet as pkt
from pox.lib.recoco import Timer
import time
import random
import json


log = core.getLogger()

 
s1_dpid=0
s2_dpid=0
s3_dpid=0
s4_dpid=0
s5_dpid=0

 
s1_p1=0
s1_p4=0
s1_p5=0
s1_p6=0
s2_p1=0
s3_p1=0
s4_p1=0


pre_s1_p1=0
pre_s1_p4=0
pre_s1_p5=0
pre_s1_p6=0
pre_s2_p1=0
pre_s3_p1=0
pre_s4_p1=0


turn=0


start_time = 0.0
received_time1 = 0.0
received_time2 = 0.0
src_dpid=0
dst_dpid=0
mytimer = 0
OWD1=0.0
OWD2=0.0
OWD3=0.0
OWD4=0.0
send_time1 = 0.0
send_time2 = 0.0
send_time3 = 0.0
send_time4 = 0.0
avg2 = 0.0
count2 = 0.0
avg3 = 0.0
count3 = 0.0
avg4 = 0.0
count4 = 0.0

delay2 = 0.0
delay3 = 0.0
delays2 =[]
delays3 =[]
delays4 =[]
delays = [[],[],[]]
delays_accept=[]
switch_accept=[]
MAX_delay = 70


def add_port_mapping_flow_entry(in_port, out_port):
  msg = of.ofp_flow_mod()
  msg.priority = 10
  msg.idle_timeout = 0
  msg.hard_timeout = 0
  msg.match.in_port = in_port
  msg.match.dl_type = 0x0800
  msg.actions.append(of.ofp_action_output(port=out_port))
  return msg

def add_address_mapping_flow_entry(dst_address, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =100
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.dl_type = 0x0800
    msg.match.nw_dst = dst_address
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg


def add_port_and_address_mapping_flow_entry(in_port, dst_address, out_port):
  msg = of.ofp_flow_mod()
  msg.priority = 10
  msg.idle_timeout = 0
  msg.hard_timeout = 0
  msg.match.in_port = in_port
  msg.match.nw_dst = dst_address
  msg.match.dl_type = 0x0800
  msg.actions.append(of.ofp_action_output(port=out_port))
  return msg

# This message tells how to forward ARP packets to routers S2, S3, and S4.
def add_arp_port_mapping_flow_entry(in_port, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =10
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.in_port = in_port
    msg.match.dl_type=0x0806
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg


# This PacketOut message provides information to switches S1 and S5 about the IP address associated with each of their ports.
def append_packet_out_with_output_port(packet, out_port):
    msg = of.ofp_packet_out(data=packet)			# Create packet_out message; use the incoming packet as the data for the packet out
    msg.actions.append(of.ofp_action_output(port=out_port))		# Add an action to send to the specified port
    return msg


class Flow:
  def __init__(self, h_src, h_dst):
    self.h_src = h_src
    self.h_dst = h_dst

  def __str__(self):
    return "Flow between H{} and H{}".format(self.h_src, self.h_dst)

  def is_equal(self, flow):
    if flow == None:
      return False

    if self.h_src == flow.h_src and self.h_dst == flow.h_dst:
      return True
    return False

class Network_Balance:

  def __init__(self):
    self.route_table = [0, 0, 0]
    self.s1_dpid = 0
    self.s5_dpid = 0
    self.openflow = None
    self.route_table_flow = []
    self.intented_flow = None
    self.intented_flow_route = 0
    self.intented_flow_limit = 0
  def create_flow(self, event, s_dpid):
    h_src = 0
    h_dst = 0
    packet = event.parsed.find('ipv4')
    if s_dpid == s1_dpid:
      if packet.srcip =="10.0.0.1":
        h_src = 1
      elif packet.srcip =="10.0.0.2":
        h_src = 2
      elif packet.srcip =="10.0.0.3":
        h_src = 3
      if packet.dstip =="10.0.0.4":
        h_dst = 4
      elif packet.dstip =="10.0.0.5":
        h_dst = 5
      elif packet.dstip =="10.0.0.6":
        h_dst = 6
    return Flow(h_src, h_dst)


  def increment_route_counter(self, route, n):
    self.route_table[route - 1] += n


  def choose_route(self):
    min_value = min(self.route_table)
    min_index = self.route_table.index(min_value)
    return min_index + 1

  def transit_routing(self, event):
    # ARP ----------------------------------------------
    msg = add_arp_port_mapping_flow_entry(in_port=1, out_port=2)
    event.connection.send(msg)
    msg = add_arp_port_mapping_flow_entry(in_port=2, out_port=1)
    event.connection.send(msg)

    # IP ----------------------------------------------
    msg = add_port_mapping_flow_entry(in_port=1, out_port=2)
    event.connection.send(msg)
    msg = add_port_mapping_flow_entry(in_port=2, out_port=1)
    event.connection.send(msg)

  def add_flow_to_route(self, flow, route):
    # for s1
    msg = add_port_and_address_mapping_flow_entry(in_port=flow.h_src, dst_address="10.0.0.{}".format(flow.h_dst), out_port=route+3)
    self.openflow.getConnection(self.s1_dpid).send(msg)
    msg = add_port_and_address_mapping_flow_entry(in_port=route + 3, dst_address="10.0.0.{}".format(flow.h_src),out_port=flow.h_src)
    self.openflow.getConnection(self.s1_dpid).send(msg)
    # for s5
    msg = add_port_and_address_mapping_flow_entry(in_port=flow.h_dst, dst_address="10.0.0.{}".format(flow.h_src), out_port=route)
    self.openflow.getConnection(self.s5_dpid).send(msg)
    msg = add_port_and_address_mapping_flow_entry(in_port=route, dst_address="10.0.0.{}".format(flow.h_dst), out_port=flow.h_dst)
    self.openflow.getConnection(self.s5_dpid).send(msg)

  def set_flow_route(self, route, flow):
    if self.does_flow_exist(flow) == True:
      self.replace_flow_route(flow, route)
      self.add_flow_to_route(flow, route)
    else:
      self.add_flow_to_route(flow, route)
      self.route_table_flow.append((flow, route))
      self.increment_route_counter(route, 1)
    self.show_flow_route_map()


  def replace_flow_route(self, flow, new_route):
    index = 0
    old_route = 0
    for x in range(len(self.route_table_flow)):
      flow_from_list, old_route = self.route_table_flow[x]
      if flow_from_list.is_equal(flow):
        break
      index += 1
    self.route_table_flow.pop(index)
    self.route_table_flow.append((flow, new_route))
    self.increment_route_counter(old_route, -1)
    self.increment_route_counter(new_route, 1)


  def does_flow_exist(self, checked_flow):
    a = self.route_table_flow
    for x in range(len(a)):
      flow, route = a[x]
      if flow.is_equal(checked_flow):
        return True
    return False


  def show_flow_route_map(self):
    a = self.route_table_flow


    for x in range(len(a)):
      flow, route = a[x]
      if flow.is_equal(self.intented_flow):
        print("[->", flow, "route", route, "<-]")
      else:
        print("[ ", flow, "route", route, " ]")


  def do_balance(self):
    if abs(self.route_table[0]-self.route_table[1]) > 1:
      return True
    if abs(self.route_table[0]-self.route_table[2]) > 1:
      return True
    if abs(self.route_table[2]-self.route_table[1]) > 1:
      return True
    return False


  def max_route(self):
    max = 0
    index = 0
    i = 1
    for x in self.route_table:
      if x > max:
        max = x
        index = i
      i += 1
    return index


  def min_route(self):
    min = 100
    index = 0
    i = 1
    for x in self.route_table:
      if x < min:
        min = x
        index = i
      i += 1
    return index


  def select_flow_from_route(self, route):
    for temp_flow, temp_route in self.route_table_flow:
      if temp_route == route and (not temp_flow.is_equal(self.intented_flow)):
        return temp_flow
  def install_arp_s1(self, event, packet):
    if packet.protodst == "10.0.0.4":
      msg = append_packet_out_with_output_port(event.ofp, 4)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.5":
      msg = append_packet_out_with_output_port(event.ofp, 4)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.6":
      msg = append_packet_out_with_output_port(event.ofp, 4)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.1":
      msg = append_packet_out_with_output_port(event.ofp, 1)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.2":
      msg = append_packet_out_with_output_port(event.ofp, 2)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.3":
      msg = append_packet_out_with_output_port(event.ofp, 3)
      event.connection.send(msg)

  def install_arp_s5(self, event, packet):
    if packet.protodst == "10.0.0.4":
      msg = append_packet_out_with_output_port(event.ofp, 4)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.5":
      msg = append_packet_out_with_output_port(event.ofp, 5)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.6":
      msg = append_packet_out_with_output_port(event.ofp, 6)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.1":
      msg = append_packet_out_with_output_port(event.ofp, 1)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.2":
      msg = append_packet_out_with_output_port(event.ofp, 1)
      event.connection.send(msg)
    if packet.protodst == "10.0.0.3":
      msg = append_packet_out_with_output_port(event.ofp, 1)
      event.connection.send(msg)


network_balancer = Network_Balance()

class myproto(packet_base):
  "My Protocol packet struct"

  def __init__(self):
     packet_base.__init__(self)
     self.timestamp=0

  def hdr(self, payload):
     return struct.pack('!I', self.timestamp)
 

def getTheTime():  #function to create a timestamp
  flock = time.localtime()
  then = "[%s-%s-%s" %(str(flock.tm_year),str(flock.tm_mon),str(flock.tm_mday))


  if int(flock.tm_hour)<10:
    hrs = "0%s" % (str(flock.tm_hour))
  else:
    hrs = str(flock.tm_hour)
  if int(flock.tm_min)<10:
    mins = "0%s" % (str(flock.tm_min))
  else:
    mins = str(flock.tm_min)


  if int(flock.tm_sec)<10:
    secs = "0%s" % (str(flock.tm_sec))
  else:
    secs = str(flock.tm_sec)
 
  then +="]%s.%s.%s" % (hrs,mins,secs)

  return then


def _timer_func ():	
																																																																																							
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid,turn
  global start_time, send_time1, send_time2,send_time3,send_time4,count4
  if s1_dpid !=0 and not core.openflow.getConnection(s1_dpid) is None:
    core.openflow.getConnection(s1_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    send_time1=time.time() * 1000*10 - start_time #sending time of stats_req: ctrl => switch0

    #sequence of packet formating operations optimised to reduce the delay variation of e-2-e measurements (to measure T3)
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("1:0:0:0:0:1")
    e.dst = EthAddr("1:0:0:0:0:2")
    e.type=0x5577 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=4)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - start_time) #set the timestamp in the probe packet
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1_dpid).send(msg)
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("1:0:0:0:0:1")
    e.dst = EthAddr("1:0:0:0:0:3")
    e.type=0x5577 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=5)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - start_time) #set the timestamp in the probe packet
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1_dpid).send(msg)
    
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("1:0:0:0:0:1")
    e.dst = EthAddr("1:0:0:0:0:4")
    e.type=0x5577 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=6)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - start_time) #set the timestamp in the probe packet
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1_dpid).send(msg)
    

  if s2_dpid !=0 and not core.openflow.getConnection(s2_dpid):
    send_time2=time.time() * 1000*10 - start_time
    core.openflow.getConnection(s2_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

  if s3_dpid !=0 and not core.openflow.getConnection(s3_dpid):  
    send_time3=time.time() * 1000*10 - start_time
    core.openflow.getConnection(s3_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

  if s4_dpid !=0 and not core.openflow.getConnection(s4_dpid):
    send_time4=time.time() * 1000*10 - start_time
    core.openflow.getConnection(s4_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

  # below, routing in s1 towards h4 (IP=10.0.0.4) is set according to the value of the variable turn
  # turn controls the round robin operation
  # turn=0/1/2 => route through s2/s3/s4, respectively


def _handle_portstats_received (event):

  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid

  global s1_p1,s1_p4, s1_p5, s1_p6, s2_p1, s3_p1, s4_p1

  global pre_s1_p1,pre_s1_p4, pre_s1_p5, pre_s1_p6, pre_s2_p1, pre_s3_p1, pre_s4_p1
  global OWD1, OWD2, OWD3, OWD4, start_time,send_time4,send_time2,send_time3,send_time1

																																																																																								

  recived_time = time.time()*1000*10-start_time
  if event.connection.dpid==s1_dpid: # The DPID of one of the switches involved in the link
    OWD1= (recived_time - send_time1)*0.5

    for f in event.stats:
      if int(f.port_no)<65534:
        if f.port_no==1:
          pre_s1_p1=s1_p1
          s1_p1=f.rx_packets
        if f.port_no==4:
          pre_s1_p4=s1_p4
          s1_p4=f.tx_packets
        if f.port_no==5:
          pre_s1_p5=s1_p5
          s1_p5=f.tx_packets
        if f.port_no==6:
          pre_s1_p6=s1_p6
          s1_p6=f.tx_packets


  if event.connection.dpid==s2_dpid:
     OWD2 = (recived_time - send_time2)*0.5
     for f in event.stats:
       if int(f.port_no)<65534:
         if f.port_no==1:
           pre_s2_p1=s2_p1
           s2_p1=f.rx_packets


  if event.connection.dpid==s3_dpid:
     OWD3 = (recived_time - send_time3)*0.5
     for f in event.stats:
        if int(f.port_no)<65534:
          if f.port_no==1:
            pre_s3_p1=s3_p1
            s3_p1=f.rx_packets


  if event.connection.dpid==s4_dpid:
    OWD4 = (recived_time - send_time4)*0.5
    for f in event.stats:
        if int(f.port_no)<65534:
          if f.port_no==1:
            pre_s4_p1=s4_p1
            s4_p1=f.rx_packets


def _handle_ConnectionUp (event):
  # waits for connections from all switches, after connecting starts the round robin timer for h1-h4 routing changes
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid


  #remember the connection dpid for the switch

  for m in event.connection.features.ports:
    if m.name == "s1-eth1":
      s1_dpid = event.connection.dpid
      network_balancer.s1_dpid = s1_dpid

    elif m.name == "s2-eth1":
      s2_dpid = event.connection.dpid
    elif m.name == "s3-eth1":
      s3_dpid = event.connection.dpid
    elif m.name == "s4-eth1":
      s4_dpid = event.connection.dpid
    elif m.name == "s5-eth1":
      s5_dpid = event.connection.dpid
      network_balancer.s5_dpid= s5_dpid
 

  # start 1-second recurring loop timer for round-robin routing changes; _timer_func to be called after expiration to change the flow entry in s1

  if s1_dpid<>0 and s2_dpid<>0 and s3_dpid<>0 and s4_dpid<>0 and s5_dpid<>0:
    Timer(1, _timer_func, recurring=True)
 
def get_intent_values():
  with open('intents.json') as f:
    data = json.load(f)

  global src_host 
  global dst_host
  global max_delay

  for intent in data.values():
    if intent["id"] == 1:
        src_host = intent["src_host"]
        dst_host = intent["dst_host"]
        max_delay = intent["max_delay"]
        break

  return src_host, dst_host, max_delay



def _handle_PacketIn(event):


  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid,dst_dpid,start_time
  global OWD1,OWD2,OWD3,OWD4
  global network_balancer
  global avg4, count4,avg3, count3,avg2, count2 
  global delay2,delay3, delay4
  global delays2, delays3, delays4, delays, delays_accept, switch_accept, MAX_delay
  network_balancer.openflow = core.openflow
  received_time = time.time() * 1000*10 - start_time
  packet = event.parsed


  if packet.type==0x5577 and event.connection.dpid==s2_dpid:
    c=packet.find('ethernet').payload
    d,=struct.unpack('!I',c)
    delay2 = int(received_time - d - OWD1-OWD2)/10
    delays2 =["s1", "s2", delay2, 1, s2_dpid]
    
  if packet.type==0x5577 and event.connection.dpid==s3_dpid:
    c=packet.find('ethernet').payload
    d,=struct.unpack('!I',c)
    delay3 = int(received_time - d - OWD1-OWD3)/10
    delays3 =["s1", "s3", delay3, 2, s3_dpid]
    
  if packet.type==0x5577 and event.connection.dpid==s4_dpid:
    c=packet.find('ethernet').payload
    d,=struct.unpack('!I',c)
    delay4 = int(received_time - d - OWD1-OWD4)/10
    delays4 =["s1", "s4", delay4, 3, s4_dpid]

    delays = [delays2, delays3, delays4]



  if event.connection.dpid==s1_dpid:

    packet=event.parsed.find('arp')
    if packet:
      network_balancer.install_arp_s1(event, packet)

    else:
      flow = network_balancer.create_flow(event, s1_dpid)
      if network_balancer.does_flow_exist(flow) == False:
        intent=get_intent_values()
        if flow.h_src == intent[0] and flow.h_dst== intent[1]: 
          max_delay = intent[2]  

          print("New flow identified based on intent: ")
          print(flow)
          print "Max delay:" + str(max_delay)
          if len(delays2)>2 and len(delays3)>2 and len(delays4)>2:
            delays_accept = handle_delays(delays, max_delay)

          if len(delays_accept) == 1:
            delay_route = delays_accept[0]
            route = delay_route[3]
            print "Selected route: " + str(route)
            network_balancer.route_table_flow.append((flow, route))
            network_balancer.increment_route_counter(route, 1)
            print "Route Table: " + str(network_balancer.route_table)
            network_balancer.add_flow_to_route(flow, route)
          elif len(delays_accept) >= 2:

            accept_route = []
            for delays in delays_accept:
              accept_route.append(delays[3])
            min_route = network_balancer.choose_route()

            route = search_route_accept(accept_route, min_route)

            if not route:
              random_route = accept_route[1]
              print("Selected route: ", random_route)
              network_balancer.route_table_flow.append((flow, random_route))
              network_balancer.increment_route_counter(random_route, 1)
              print("Route Table:", network_balancer.route_table)
              network_balancer.add_flow_to_route(flow, random_route)
            else:
              network_balancer.add_flow_to_route(flow, route)
              print("Selected route: ", route)
              network_balancer.route_table_flow.append((flow, route))
              network_balancer.increment_route_counter(route, 1)
              print("Route Table:", network_balancer.route_table)
              network_balancer.add_flow_to_route(flow, route)

        else:
          print("Identified new flow:")
          print(flow)
          route = network_balancer.choose_route()
          print "Selected route: " + str(route)
          network_balancer.route_table_flow.append((flow,route))
          network_balancer.increment_route_counter(route, 1)
          
          print "Route Table: " + str(network_balancer.route_table)
          network_balancer.add_flow_to_route(flow, route)


 
  elif event.connection.dpid==s2_dpid:
    network_balancer.transit_routing(event)

  elif event.connection.dpid==s3_dpid:
    network_balancer.transit_routing(event)

  elif event.connection.dpid==s4_dpid:
    network_balancer.transit_routing(event)

  elif event.connection.dpid==s5_dpid: 

    packet=event.parsed.find('arp')
    if packet:
      network_balancer.install_arp_s5(event, packet)



def handle_delays(delays, max_delay):
    delays_accept = []
    for delay in delays:
        if delay[2] <= max_delay:
            delays_accept.append(delay)
    return delays_accept



def search_route_accept(accept_route, min_route):
  for i in accept_route:
    if i == min_route:
      return i
  return False

def launch ():

  global start_time
  start_time = time.time()*1000*10
  # core is an instance of class POXCore (EventMixin) and it can register objects
  # an object xxx can be registered to core instance which makes the object "component" available as pox.core.core.xxx
  # for examplese see e.g. https://noxrepo.github.io/pox-doc/html/#the-openflow-nexus-core-openflow




  core.openflow.addListenerByName("PortStatsReceived",_handle_portstats_received) # listen for port stats , https://noxrepo.github.io/pox-doc/html/#statistics-events
  core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp) # listen for the establishment of a new control channel with a switch, https://noxrepo.github.io/pox-doc/html/#connectionup
  core.openflow.addListenerByName("PacketIn",_handle_PacketIn) # listen for the reception of packet_in message from switch, https://noxrepo.github.io/pox-doc/html/#packetin

 
