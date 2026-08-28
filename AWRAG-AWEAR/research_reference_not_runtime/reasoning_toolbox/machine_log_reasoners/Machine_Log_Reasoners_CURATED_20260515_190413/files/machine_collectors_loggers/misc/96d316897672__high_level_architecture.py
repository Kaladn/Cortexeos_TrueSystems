#!/usr/bin/env python3
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.programming.framework import React
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL
from diagrams.generic.network import Firewall
from diagrams.onprem.network import Nginx
from diagrams.onprem.client import User
from diagrams.onprem.analytics import Spark
from diagrams.aws.ml import Rekognition
from diagrams.aws.security import Shield

# Create a diagram for the high-level NEXUS architecture
with Diagram("NEXUS: The Collective OS - High Level Architecture", show=False, direction="TB", filename="high_level_architecture"):
    
    # User interaction
    user = User("User Interface")
    
    # Defense Protocols (outer layer)
    with Cluster("Defense Protocols"):
        defense = Shield("Security Layer")
        firewall = Firewall("Input Validation")
        
        # OS Kernel (core)
        with Cluster("OS Kernel"):
            kernel = Server("Resource Management")
            storage = Storage("Temporal Storage")
            
            # Multi-Agent Synergy Core
            with Cluster("Multi-Agent Synergy Core"):
                agents = [
                    Python("Historian"),
                    Python("Strategist"),
                    Python("Translator"),
                    Python("Watchdog"),
                    Python("Empath")
                ]
                
                # Emotional Simulation Engine
                emotion = Rekognition("Emotional Simulation Engine")
                
                # Memory Web
                memory = SQL("Memory Web")
                
                # Connect agents to each other
                for i in range(len(agents)):
                    for j in range(len(agents)):
                        if i != j:
                            agents[i] >> Edge(color="gray", style="dotted") >> agents[j]
                
                # Connect agents to emotional engine and memory
                for agent in agents:
                    agent >> emotion
                    agent >> memory
                    memory >> agent
        
        # Optional Chaos Mode
        chaos = Spark("Optional Chaos Mode")
    
    # Connect user to system through defense
    user >> firewall >> kernel
    
    # Connect kernel to defense for output validation
    kernel >> defense >> user
    
    # Connect chaos mode to kernel
    chaos >> kernel
