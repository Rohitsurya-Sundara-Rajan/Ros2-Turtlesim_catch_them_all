#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn
from functools import partial
import random
import math
from my_robot_interfaces.msg import Turtle
from my_robot_interfaces.msg import TurtleAray
from my_robot_interfaces.srv import CatchTurtle
from turtlesim.srv import Kill



class TurtleSpawnerNode(Node):
    def __init__(self):
        super().__init__("turtle_spawner")
        self.declare_parameter("turtle_name_prefix", "turtle")
        self.declare_parameter("spawn_frequency", 1.0)
        self.turtle_name_prefix = self.get_parameter("turtle_name_prefix").value
        self.spawn_frequency = self.get_parameter("spawn_frequency").value
        self.turtle_counter = 0
        self.alive_turtle = []
        self.alive_turtle_publisher = self.create_publisher(TurtleAray, "alive_turtles", 10)
        self.spawn_client = self.create_client(Spawn, "/spawn")
        self.kill_client = self.create_client(Kill, "/kill")
        self.catch_turtle_service = self.create_service(CatchTurtle, "catch_turtle", self.callback_catch_turtle)
        self.spawn_turtle_timer = self.create_timer(1.0/self.spawn_frequency, self.spawn_new_turtle)

    def callback_catch_turtle(self, request: CatchTurtle.Request, response: CatchTurtle.Response):
        self.call_kill_service(request.name)
        response.success = True
        return response

    def publish_alive_turtles(self):
        msg = TurtleAray()
        msg.turtles = self.alive_turtle
        self.alive_turtle_publisher.publish(msg)

    def spawn_new_turtle(self):
        self.turtle_counter +=1
        name = self.turtle_name_prefix + str(self.turtle_counter)
        x = random.uniform(0.0, 11.0)
        y = random.uniform(0.0, 11.0)
        theta = random.uniform(0.0, 2*math.pi)
        self.call_spawn_service(name, x, y, theta)

    def call_spawn_service(self, turtle_name, x, y, theta):
        while not self.spawn_client.wait_for_service(1.0):
            self.get_logger().warn("Waiting for spawn service...")

        request = Spawn.Request()
        request.x = x
        request.y = y
        request.theta = theta
        request.name = turtle_name

        future = self.spawn_client.call_async(request)
        future.add_done_callback(partial(self.callback_call_spawn_service, request=request))
    
    def callback_call_spawn_service(self, future, request: Spawn.Request):
        try:
            response: Spawn.Response = future.result()  # Get the result from the future
            if response.name != "":
                self.get_logger().info(f"New alive turtle: {response.name}")
                new_turtle = Turtle()
                new_turtle.name = response.name
                new_turtle.x = request.x
                new_turtle.y = request.y
                new_turtle.theta = request.theta
                self.alive_turtle.append(new_turtle)
                self.publish_alive_turtles()
            else:
                self.get_logger().warn("Failed to spawn turtle.")
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")


    def call_kill_service(self, turtle_name):
        while not self.spawn_client.wait_for_service(1.0):
            self.get_logger().warn("Waiting for kill service...")

        request = Kill.Request()
        request.name = str(turtle_name)

        future = self.kill_client.call_async(request)
        future.add_done_callback(partial(self.call_kill_service, turtle_name=turtle_name))

    def callback_call_kill_service(self, future, turtle_name):
        for (i, turtle) in enumerate(self.alive_turtle):
            if turtle.name == turtle_name:
                del self.alive_turtle[i]
                self.publish_alive_turtles()
                break


def main(args=None):
    rclpy.init(args=args)
    node = TurtleSpawnerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__=="__main__":
    main()