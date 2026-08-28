"""
Neo4j Causal Graph Builder
Stores 6-1-6 analysis results in Neo4j graph database
"""


class CausalGraphBuilder:
    """Builds causal graphs in Neo4j from analysis results"""
    
    def __init__(self, neo4j_connector, config):
        """
        Initialize graph builder
        
        Args:
            neo4j_connector: Neo4jConnector instance
            config: Configuration dictionary
        """
        self.neo4j = neo4j_connector
        self.config = config
    
    def build(self, ticker, market_data, capsules, causal_results, patterns):
        """
        Build complete causal graph in Neo4j
        
        Graph structure:
        - TradingDay nodes (one per day)
        - PRECEDES relationships (temporal sequence)
        - CAUSES relationships (high causal consistency)
        - Pattern break and anomaly markers
        
        Args:
            ticker: Stock/crypto ticker symbol
            market_data: Raw market data
            capsules: 6-1-6 temporal capsules
            causal_results: Causal analysis results
            patterns: Detected patterns
        
        Returns:
            dict: Graph statistics
        """
        with self.neo4j.session() as session:
            # Clear existing data for this ticker
            session.run(
                "MATCH (n:TradingDay {ticker: $ticker}) DETACH DELETE n",
                ticker=ticker
            )
            
            # Create TradingDay nodes
            for capsule in capsules:
                causal = causal_results[capsule['index']]
                
                session.run("""
                    CREATE (d:TradingDay {
                        ticker: $ticker,
                        date: $date,
                        index: $index,
                        close: $close,
                        volume: $volume,
                        price_change: $price_change,
                        causal_consistency: $consistency,
                        backward_score: $backward,
                        forward_score: $forward
                    })
                """, 
                    ticker=ticker,
                    date=capsule['date'],
                    index=capsule['index'],
                    close=capsule['anchor']['close'],
                    volume=capsule['anchor']['volume'],
                    price_change=capsule['price_change'],
                    consistency=causal['consistency'],
                    backward=causal['backward_score'],
                    forward=causal['forward_score']
                )
            
            # Create PRECEDES relationships (temporal sequence)
            session.run("""
                MATCH (d1:TradingDay {ticker: $ticker})
                MATCH (d2:TradingDay {ticker: $ticker})
                WHERE d2.index = d1.index + 1
                CREATE (d1)-[:PRECEDES {
                    price_change: d2.price_change,
                    volume_change: d2.volume - d1.volume
                }]->(d2)
            """, ticker=ticker)
            
            # Create CAUSES relationships (high consistency)
            high_threshold = self.config['analysis']['causal_consistency_high']
            session.run("""
                MATCH (d1:TradingDay {ticker: $ticker})
                MATCH (d2:TradingDay {ticker: $ticker})
                WHERE d2.index = d1.index + 1
                  AND d2.causal_consistency >= $threshold
                CREATE (d1)-[:CAUSES {
                    consistency: d2.causal_consistency,
                    strength: d2.forward_score
                }]->(d2)
            """, ticker=ticker, threshold=high_threshold)
            
            # Mark pattern breaks
            for pb in patterns['pattern_breaks']:
                session.run("""
                    MATCH (d:TradingDay {ticker: $ticker, date: $date})
                    SET d.pattern_break = true,
                        d.break_type = $break_type,
                        d.break_magnitude = $magnitude
                """,
                    ticker=ticker,
                    date=pb['date'],
                    break_type=pb['type'],
                    magnitude=abs(pb['change'])
                )
            
            # Mark anomalies
            for anomaly in patterns['anomalies']:
                session.run("""
                    MATCH (d:TradingDay {ticker: $ticker, date: $date})
                    SET d.anomaly = true,
                        d.anomaly_consistency = $consistency
                """,
                    ticker=ticker,
                    date=anomaly['date'],
                    consistency=anomaly['consistency']
                )
            
            # Get graph statistics
            stats = session.run("""
                MATCH (d:TradingDay {ticker: $ticker})
                OPTIONAL MATCH (d)-[r:CAUSES]->()
                RETURN count(d) as node_count,
                       count(r) as causal_edge_count
            """, ticker=ticker).single()
            
            return {
                'node_count': stats['node_count'],
                'causal_edge_count': stats['causal_edge_count']
            }
