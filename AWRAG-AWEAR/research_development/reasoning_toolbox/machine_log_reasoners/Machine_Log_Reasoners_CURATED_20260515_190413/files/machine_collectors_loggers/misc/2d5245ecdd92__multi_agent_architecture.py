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

# Create a diagram for the Multi-Agent Synergy Core
with Diagram("NEXUS Multi-Agent Synergy Core", show=False, direction="TB", filename="multi_agent_architecture"):
    
    # User input
    user = User("User Input")
    
    # Multi-Agent Synergy Core
    with Cluster("Multi-Agent Synergy Core"):
        # Agent Registry
        registry = SQL("Agent Registry")
        
        # Role Manager
        role_manager = Server("Role Manager")
        
        # Communication Bus
        comm_bus = Nginx("Communication Bus")
        
        # Consensus Engine
        consensus = Spark("Consensus Engine")
        
        # Orchestration Layer
        orchestration = React("Orchestration Layer")
        
        # Knowledge Distillation Module
        distillation = Python("Knowledge Distillation")
        
        # Specialized Agents
        with Cluster("Specialized Agents"):
            historian = Python("Historian")
            strategist = Python("Strategist")
            translator = Python("Translator")
            watchdog = Python("Watchdog")
            empath = Rekognition("Empath")
        
        # Connect components
        registry >> role_manager
        role_manager >> comm_bus
        comm_bus >> consensus
        consensus >> orchestration
        orchestration >> distillation
        
        # Connect agents to communication bus
        historian >> comm_bus
        strategist >> comm_bus
        translator >> comm_bus
        watchdog >> comm_bus
        empath >> comm_bus
        
        # Connect communication bus to agents
        comm_bus >> historian
        comm_bus >> strategist
        comm_bus >> translator
        comm_bus >> watchdog
        comm_bus >> empath
    
    # Connect user to system
    user >> comm_bus
    distillation >> user
