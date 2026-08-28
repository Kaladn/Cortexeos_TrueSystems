            age_days = (datetime.now() - ref_date).days
            
            # Apply grace period
            effective_age_days = max(0, age_days - decay_config['grace_period_days'])
            
            # Calculate decay factor
            if effective_age_days <= 0:
                return 0.0
            else:
                # Convert rate from yearly to daily
                daily_rate = decay_config['rate'] / 365
                
                # Calculate decay
                decay_factor = effective_age_days * daily_rate
                
                # Cap decay factor at 0.5 (never reduce score by more than 50%)
                return min(0.5, decay_factor)
                
        except ValueError:
            return 0.0  # No decay if date parsing fails
    
    def _update_average_scores(self, source_type: str, score: float) -> None:
        """
        Update average scores in statistics.
        
        Args:
            source_type: Source type
            score: Credibility score
        """
        # Get current totals
        total_assessments = self.stats['total_assessments']
        
        if total_assessments <= 1:
            # First assessment, set averages directly
            self.stats['avg_credibility_score'] = score
            
            if source_type == 'academic':
                self.stats['avg_academic_score'] = score
            elif source_type == 'technical':
                self.stats['avg_technical_score'] = score
            elif source_type == 'web':
                self.stats['avg_web_score'] = score
        else:
            # Update running averages
            prev_total = total_assessments - 1
            
            self.stats['avg_credibility_score'] = (
                (self.stats['avg_credibility_score'] * prev_total + score) / total_assessments
            )
            
            if source_type == 'academic':
                academic_sources = self.stats['academic_sources']
                if academic_sources <= 1:
                    self.stats['avg_academic_score'] = score
                else:
                    self.stats['avg_academic_score'] = (
                        (self.stats['avg_academic_score'] * (academic_sources - 1) + score) / academic_sources
                    )
            elif source_type == 'technical':
                technical_sources = self.stats['technical_sources']
                if technical_sources <= 1:
                    self.stats['avg_technical_score'] = score
                else:
                    self.stats['avg_technical_score'] = (
                        (self.stats['avg_technical_score'] * (technical_sources - 1) + score) / technical_sources
                    )
            elif source_type == 'web':
                web_sources = self.stats['web_sources']
                if web_sources <= 1:
                    self.stats['avg_web_score'] = score
                else:
                    self.stats['avg_web_score'] = (
                        (self.stats['avg_web_score'] * (web_sources - 1) + score) / web_sources
                    )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get assessment statistics.
        
        Returns:
            Assessment statistics
        """
        return self.stats
    
    def print_stats(self) -> None:
        """Print assessment statistics to console"""
        print("\n" + "="*50)
        print(" SOURCE CREDIBILITY ASSESSMENT - STATISTICS")
        print("="*50)
        
        print(f"Total assessments: {self.stats['total_assessments']}")
        print(f"Academic sources: {self.stats['academic_sources']}")
        print(f"Technical sources: {self.stats['technical_sources']}")
        print(f"Web sources: {self.stats['web_sources']}")
        print(f"Unknown sources: {self.stats['unknown_sources']}")
        
        print("\nAverage Scores:")
        print(f"  Overall: {self.stats['avg_credibility_score']:.2f}")
        print(f"  Academic: {self.stats['avg_academic_score']:.2f}")
        print(f"  Technical: {self.stats['avg_technical_score']:.2f}")
        print(f"  Web: {self.stats['avg_web_score']:.2f}")
        
        print("="*50 + "\n")


# Test the Source Credibility Assessment if run directly
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("/home/ubuntu/nexus_project/knowledge_validation/logs", exist_ok=True)
    
    # Create the Source Credibility Assessment
    assessor = SourceCredibilityAssessment()
    
    # Test with academic source
    academic_source = {
        'url': 'https://pubmed.ncbi.nlm.nih.gov/35793824/',
        'type': 'academic',
        'origin': 'Nature',
        'publisher': 'Nature',
        'impact_factor': 9.2,
        'author_history_score': 0.87,
        'publication_date': '2022-05-01',
        'peer_reviewed': True
    }
    
    # Test with technical source
    technical_source = {
        'url': 'https://docs.microsoft.com/en-us/azure/security/fundamentals/encryption-overview',
        'type': 'technical',
        'origin': 'Microsoft Documentation',
        'organization': 'Microsoft',
        'documentation_quality': 0.9,
        'update_date': '2023-10-15',
        'community_endorsement': 0.8
    }
    
    # Test with web source
    web_source = {
        'url': 'https://www.bbc.com/news/technology-12345678',
        'type': 'web',
        'origin': 'BBC News',
        'content_quality': 0.8,
        'reference_quality': 0.7,
        'publication_date': '2024-01-15'
    }
    
    # Assess sources
    print("\nAssessing academic source...")
    academic_result = assessor.assess_source_credibility(academic_source)
    print(f"Result: {json.dumps(academic_result, indent=2)}")
    
    print("\nAssessing technical source...")
    technical_result = assessor.assess_source_credibility(technical_source)
    print(f"Result: {json.dumps(technical_result, indent=2)}")
    
    print("\nAssessing web source...")
    web_result = assessor.assess_source_credibility(web_source)
    print(f"Result: {json.dumps(web_result, indent=2)}")
    
    # Print statistics
    assessor.print_stats()
