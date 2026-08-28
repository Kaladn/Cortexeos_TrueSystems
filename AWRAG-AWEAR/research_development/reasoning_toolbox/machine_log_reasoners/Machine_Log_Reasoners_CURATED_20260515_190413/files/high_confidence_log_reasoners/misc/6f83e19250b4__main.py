import os
import uuid
from datetime import datetime

from ingestion.corpus_loader import CorpusLoader
from ingestion.tokenizer_normalizer import TokenizerNormalizer
from ingestion.window_builder import WindowBuilder
from ingestion.ncv73_builder import NCV73Builder
from ingestion.persistence_writer import PersistenceWriter

from runtime.anchor_extractor import AnchorExtractor
from runtime.context_retriever import ContextRetriever
from runtime.cascade_engine import CascadeEngine
from runtime.causal_validator import CausalValidator
from runtime.report_builder import ReportBuilder
from runtime.llm_shim import LLMShim

from neo4j.graph_mapper import GraphMapper

class YourNightmareWorker:
    def __init__(self, config):
        self.config = config
        self.session_dir = self.get_session_dir()
        self.config["data_dir"] = os.path.join(self.session_dir, "yournightmare_data")
        os.makedirs(self.config["data_dir"], exist_ok=True)

        # Ingestion components
        self.corpus_loader = CorpusLoader(self.config)
        self.tokenizer = TokenizerNormalizer(self.config)
        self.window_builder = WindowBuilder(self.config)
        self.ncv_builder = NCV73Builder(self.config)
        self.persistence_writer = PersistenceWriter(self.config)

        # Runtime components
        self.anchor_extractor = AnchorExtractor(self.config)
        self.context_retriever = ContextRetriever(self.config)
        self.cascade_engine = CascadeEngine(self.config)
        self.causal_validator = CausalValidator(self.config)
        self.report_builder = ReportBuilder(self.config)
        self.llm_shim = LLMShim(self.config)

        # Neo4j component
        self.graph_mapper = GraphMapper(self.config)

    def get_session_dir(self):
        """Determines the session directory based on the new file system rules."""
        today = datetime.now().strftime("%Y-%m-%d")
        session_uuid = str(uuid.uuid4())
        session_dir = os.path.join("memory", today, session_uuid)
        os.makedirs(session_dir, exist_ok=True)
        print(f"[YourNightmareWorker] Session directory: {session_dir}")
        return session_dir

    def run_ingestion(self, doc_ids, corpus_id):
        """Runs the full ingestion pipeline."""
        print("\n--- RUNNING INGESTION PIPELINE ---")
        # 1. Load documents
        docs = self.corpus_loader.load_documents(doc_ids, corpus_id)

        # 2. Tokenize and normalize
        all_tokens = []
        for doc_id, raw_text in docs:
            tokens = self.tokenizer.process(doc_id, raw_text)
            all_tokens.extend(tokens)

        # 3. Build windows
        self.window_builder.process(all_tokens)
        lexicon_counts = self.window_builder.get_lexicon_counts()

        # 4. Build NCVs
        lexicon = self.ncv_builder.build_lexicon(lexicon_counts)
        contexts = {}
        for word in lexicon:
            contexts[word] = self.ncv_builder.build_ncv(word, lexicon)

        # 5. Persist data
        self.persistence_writer.write_lexicon(lexicon)
        self.persistence_writer.write_contexts(contexts)
        self.persistence_writer.write_doc_index(all_tokens)

        # 6. Map to graph
        self.graph_mapper.map_to_graph(lexicon, contexts)
        print("--- INGESTION PIPELINE COMPLETE ---")

    def run_query(self, query):
        """Runs the full query pipeline."""
        print(f"\n--- RUNNING QUERY PIPELINE for query: [32m'{query}'[0m ---")
        # 1. Extract anchors
        anchors_data = self.anchor_extractor.extract(query)
        anchors = anchors_data["anchors"]

        # 2. Retrieve context
        context = self.context_retriever.retrieve(anchors)

        # 3. Build cascades
        cascades = self.cascade_engine.build_cascades(anchors, context)

        # 4. Validate causality
        validation_results = self.causal_validator.validate("placeholder_statement", context)

        # 5. Build report
        report = self.report_builder.build(query, anchors, context, cascades, validation_results)

        # 6. Optionally style with LLM
        if self.config["default_return_mode"] == "json+llm":
            report["llm_summary"] = self.llm_shim.style_report(report)

        print("--- QUERY PIPELINE COMPLETE ---")
        return report

if __name__ == "__main__":
    # This is a dummy main function to show how the worker would be used.
    # In a real CompuCog environment, this would be managed by the worker
    # lifecycle system.

    import yaml

    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    worker = YourNightmareWorker(config)

    # --- Run Ingestion ---
    worker.run_ingestion(doc_ids=["doc1", "doc2"], corpus_id="test_corpus")

    # --- Run Query ---
    query = "What are the remedies for breach of contract?"
    report = worker.run_query(query)

    import json
    print("\n--- DETERMINISTIC REPORT ---")
    print(json.dumps(report, indent=2))
    print("---------------------------")
