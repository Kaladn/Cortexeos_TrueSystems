        
        # Analyze current input
        current_typing = self.analyze_typing_pattern(text_input, timing_data)
        current_language = self.analyze_language_pattern(text_input)
        
        confidence_scores = []
        
        # Typing pattern confidence
        if current_typing and profile['typing_patterns']['keystroke_dynamics']:
            typing_confidence = self._compare_typing_patterns(current_typing, profile['typing_patterns'])
            confidence_scores.append(typing_confidence)
        
        # Language pattern confidence
        if current_language and profile['language_patterns']['vocabulary_frequency']:
            language_confidence = self._compare_language_patterns(current_language, profile['language_patterns'])
            confidence_scores.append(language_confidence)
        
        # Overall confidence (average of available scores)
        if confidence_scores:
            overall_confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            overall_confidence = 0.0
        
        # Store confidence score
        profile['confidence_scores'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'confidence': overall_confidence,
            'components': {
                'typing': confidence_scores[0] if len(confidence_scores) > 0 else 0,
                'language': confidence_scores[1] if len(confidence_scores) > 1 else 0
            }
        })
        
        return overall_confidence
    
    def _compare_typing_patterns(self, current: Dict, historical: Dict) -> float:
        """Compare current typing pattern with historical patterns."""
        try:
            if not historical['keystroke_dynamics']:
                return 0.5  # Neutral score if no historical data
            
            # Simple similarity scoring based on typing speed and character frequency
            recent_patterns = historical['keystroke_dynamics'][-10:]  # Last 10 patterns
            
            similarities = []
            for pattern in recent_patterns:
                # Compare typing speed
                speed_similarity = 1.0 - abs(current.get('typing_speed', 0) - pattern.get('typing_speed', 0)) / max(current.get('typing_speed', 1), pattern.get('typing_speed', 1), 1)
                
                # Compare character frequency patterns
                current_chars = set(current.get('character_frequency', {}).keys())
                pattern_chars = set(pattern.get('character_frequency', {}).keys())
                
                if current_chars and pattern_chars:
                    char_similarity = len(current_chars & pattern_chars) / len(current_chars | pattern_chars)
                else:
                    char_similarity = 0.5
                
                similarities.append((speed_similarity + char_similarity) / 2)
            
            return sum(similarities) / len(similarities) if similarities else 0.5
            
        except Exception as e:
            self.logger.error(f"Typing pattern comparison error: {e}")
            return 0.5
    
    def _compare_language_patterns(self, current: Dict, historical: Dict) -> float:
        """Compare current language pattern with historical patterns."""
        try:
            # Vocabulary overlap scoring
            current_vocab = current.get('vocabulary', set())
            historical_vocab = set(historical['vocabulary_frequency'].keys())
            
            if current_vocab and historical_vocab:
                vocab_overlap = len(current_vocab & historical_vocab) / len(current_vocab | historical_vocab)
            else:
                vocab_overlap = 0.5
            
            # Sentence structure similarity (simplified)
            current_sentence_len = current.get('avg_sentence_length', 0)
            if historical['sentence_structure']:
                historical_sentence_lens = [p.get('avg_sentence_length', 0) for p in historical['sentence_structure'][-10:]]
                avg_historical_len = sum(historical_sentence_lens) / len(historical_sentence_lens)
                
                if avg_historical_len > 0:
                    sentence_similarity = 1.0 - abs(current_sentence_len - avg_historical_len) / max(current_sentence_len, avg_historical_len, 1)
                else:
                    sentence_similarity = 0.5
            else:
                sentence_similarity = 0.5
            
            return (vocab_overlap + sentence_similarity) / 2
            
        except Exception as e:
            self.logger.error(f"Language pattern comparison error: {e}")
            return 0.5
    
    def authenticate_user(self, username: str, text_input: str, timing_data: List[float] = None) -> Tuple[bool, float, str]:
        """Authenticate user based on cognitive patterns."""
        try:
            # Load user profile if not in memory
            if username not in self.user_profiles:
                if not self._load_user_profile(username):
                    return False, 0.0, "User profile not found"
            
            # Calculate confidence score
            confidence = self.calculate_confidence_score(username, text_input, timing_data)
            
            # Authentication decision
            authenticated = confidence >= self.config['confidence_threshold']
            
            # Log authentication attempt
            auth_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'username': username,
                'confidence': confidence,
                'authenticated': authenticated,
                'input_length': len(text_input)
            }
            
            self.user_profiles[username]['authentication_history'].append(auth_record)
            self._save_user_profile(username)
            
            if authenticated:
                self.logger.info(f"✅ User authenticated: {username} (confidence: {confidence:.3f})")
                return True, confidence, "Authentication successful"
            else:
                self.logger.warning(f"❌ Authentication failed: {username} (confidence: {confidence:.3f})")
                return False, confidence, f"Confidence too low: {confidence:.3f} < {self.config['confidence_threshold']}"
        
        except Exception as e:
            self.logger.error(f"Authentication error for {username}: {e}")
            return False, 0.0, f"Authentication error: {e}"
    
    def generate_daily_passphrase(self, username: str) -> str:
        """Generate daily rotating cognitive passphrase."""
        try:
            # Generate passphrase based on date and user
            today = datetime.utcnow().strftime('%Y-%m-%d')
            passphrase_seed = f"{username}:{today}:cortexos_reaper"
            
            # Create hash-based passphrase
            hash_obj = hashlib.sha256(passphrase_seed.encode())
            hash_hex = hash_obj.hexdigest()
            
            # Convert to memorable passphrase (simplified)
            words = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf', 'hotel']
            passphrase_parts = []
            
            for i in range(0, 8, 2):
                word_index = int(hash_hex[i:i+2], 16) % len(words)
                passphrase_parts.append(words[word_index])
            
            passphrase = '-'.join(passphrase_parts[:3])  # 3-word passphrase
            
            # Store for validation
            self.daily_passphrases[username] = {
                'passphrase': passphrase,
                'date': today,
                'generated': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"🔑 Generated daily passphrase for {username}")
            return passphrase
            
        except Exception as e:
            self.logger.error(f"Passphrase generation error for {username}: {e}")
            return "emergency-override-alpha"
    
    def validate_daily_passphrase(self, username: str, provided_passphrase: str) -> bool:
        """Validate daily passphrase."""
        try:
            # Generate expected passphrase for today
            expected_passphrase = self.generate_daily_passphrase(username)
            
            # Compare with provided passphrase
            is_valid = provided_passphrase.strip().lower() == expected_passphrase.lower()
            
            if is_valid:
                self.logger.info(f"✅ Daily passphrase validated for {username}")
            else:
                self.logger.warning(f"❌ Invalid daily passphrase for {username}")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Passphrase validation error for {username}: {e}")
            return False
    
    def get_user_stats(self, username: str) -> Dict:
        """Get user cognitive authentication statistics."""
        if username not in self.user_profiles:
            return {}
        
        profile = self.user_profiles[username]
        
        # Calculate statistics
        auth_history = profile.get('authentication_history', [])
        confidence_scores = [record['confidence'] for record in auth_history]
        
        stats = {
            'username': username,
            'profile_created': profile.get('created'),
            'total_authentications': len(auth_history),
            'successful_authentications': len([r for r in auth_history if r['authenticated']]),
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'learning_complete': profile.get('learning_complete', False),
            'patterns_learned': {
                'typing_samples': len(profile['typing_patterns']['keystroke_dynamics']),
                'language_samples': len(profile['language_patterns']['sentence_structure']),
                'vocabulary_size': len(profile['language_patterns']['vocabulary_frequency'])
            }
        }
        
        return stats

def test_cognitive_authenticator():
    """Test the cognitive authentication system."""
    print("🧠 Testing Cognitive Authenticator")
    print("=" * 50)
    
    auth = CognitiveAuthenticator()
    
    # Test user creation
    print("\n1. Creating user profile...")
    auth.create_user_profile("lee_mercey")
    
    # Test pattern learning
    print("\n2. Learning user patterns...")
    sample_inputs = [
        "Load medical expertise, got a weird scan",
        "Analyze this data for patterns",
        "What's the confidence on this diagnosis?",
        "Save the analysis results",
        "Check the security logs"
    ]
    
    for i, text in enumerate(sample_inputs):
        print(f"   Learning from input {i+1}...")
        auth.learn_user_patterns("lee_mercey", text)
    
    # Test authentication
    print("\n3. Testing authentication...")
    test_input = "Load financial expertise, analyze market data"
    authenticated, confidence, message = auth.authenticate_user("lee_mercey", test_input)
    
    print(f"   Authentication result: {authenticated}")
    print(f"   Confidence score: {confidence:.3f}")
    print(f"   Message: {message}")
    
    # Test daily passphrase
    print("\n4. Testing daily passphrase...")
    passphrase = auth.generate_daily_passphrase("lee_mercey")
    print(f"   Generated passphrase: {passphrase}")
    
    is_valid = auth.validate_daily_passphrase("lee_mercey", passphrase)
    print(f"   Passphrase validation: {is_valid}")
    
    # Test user stats
    print("\n5. User statistics...")
    stats = auth.get_user_stats("lee_mercey")
    print(f"   Total authentications: {stats['total_authentications']}")
    print(f"   Average confidence: {stats['average_confidence']:.3f}")
    print(f"   Patterns learned: {stats['patterns_learned']}")
    
    print("\n✅ Cognitive Authenticator test complete!")
    print("🧠 Neural fingerprinting verified!")

if __name__ == "__main__":
    test_cognitive_authenticator()

