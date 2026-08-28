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

# Create a diagram for the Memory Web component
with Diagram("NEXUS Memory Web - Associative Knowledge System", show=False, direction="TB", filename="memory_web_architecture"):
    
    # User query
    user = User("User Query")
    
    # Memory Web components
    with Cluster("Memory Web"):
        # Knowledge Graph Foundation
        kg = SQL("Knowledge Graph Foundation")
        
        # Vector Embedding Layer
        vector = Spark("Vector Embedding Layer")
        
        # Associative Retrieval Engine
        retrieval = Server("Associative Retrieval Engine")
        
        # Reasoning Trace Module
        reasoning = Python("Reasoning Trace Module")
        
        # Growth Management System
        growth = React("Growth Management System")
        
        # Connect components
        kg >> vector
        vector >> retrieval
        retrieval >> reasoning
        reasoning >> growth
        growth >> kg
    
    # Connect user to system
    user >> kg
    reasoning >> user
