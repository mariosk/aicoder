"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module AICoder: The AICoder module.
"""

import os
import faiss
import pickle
import logging

from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
from pathlib import Path

from constants import (
    AICODER_5GCODE_PATH,
    AICODER_FAISS_INDEX_FOLDER,
    AICODER_FAISS_INDEX_FILE,
    AICODER_FAISS_INDEX_CHUNKS_FILE,
    HUGGINGFACE_TOKEN,
    AICODER_5GCODE_EXTENSIONS,
    LLMModels,
)

logger = logging.getLogger()


class AICoder:
    def __init__(self):
        """
        Initialize the AICoder object.
        """
        logger.info("Initializing AICoder...")
        # time.sleep(500)
        # Step 1: Check if FAISS index exists or create it
        logger.info("Checking for existing FAISS index...")
        # Ensure the folder exists
        Path(AICODER_FAISS_INDEX_FOLDER).mkdir(parents=True, exist_ok=True)
        self.__embedding_model = SentenceTransformer(LLMModels.EMBEDDING_MODEL.value)
        self._check_faiss_index()
        # Step 2: Load the LLM and tokenizer
        logger.info("Loading LLM and tokenizer...")
        self.__tokenizer = AutoTokenizer.from_pretrained(
            LLMModels.QUERIES_MODEL.value, token=HUGGINGFACE_TOKEN, resume_download=True, trust_remote_code=True
        )
        self.__model = AutoModelForCausalLM.from_pretrained(
            LLMModels.QUERIES_MODEL.value, token=HUGGINGFACE_TOKEN, trust_remote_code=True
        )

        logger.info("AICoder initialized.")

    def _check_faiss_index(self):
        self.__index, self.__chunks = self._load_faiss_index(AICODER_FAISS_INDEX_FILE)
        if self.__index is None or self.__chunks is None:
            logger.info(f"Index not found under '{AICODER_FAISS_INDEX_FILE}'. Extracting and chunking repository data...")
            self.__chunks = self._extract_and_chunk(AICODER_5GCODE_PATH)
            logger.info(f"Total chunks extracted: {len(self.__chunks)}")
            logger.info(f"Creating FAISS index under '{AICODER_FAISS_INDEX_FILE}'...")
            self.__index = self._create_faiss_index(self.__chunks, self.__embedding_model, AICODER_FAISS_INDEX_FILE)
            logger.info("FAISS index created and saved to disk.")
        else:
            logger.info("FAISS index loaded from disk.")

    # Step 1: Extract and chunk repository data
    def _extract_and_chunk(self, repo_path, chunk_size=500):
        """
        Extract and chunk repository data into smaller pieces.
        """
        chunks = []
        allowed_extensions = tuple(AICODER_5GCODE_EXTENSIONS.split(","))
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith(allowed_extensions):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        content = f.read()
                        for i in range(0, len(content), chunk_size):
                            chunks.append(content[i : i + chunk_size])
        return chunks

    # Step 2: Index the repository data using FAISS
    def _create_faiss_index(self, chunks, embedding_model, index_path):
        """
        Create a FAISS index for the repository chunks and save it to disk.
        """
        # Generate embeddings
        embeddings = embedding_model.encode(chunks)

        # Create the FAISS index
        index = faiss.IndexFlatL2(embeddings.shape[1])  # L2 distance index
        index.add(embeddings)

        # Save the index and chunks to disk
        faiss.write_index(index, index_path)
        with open(AICODER_FAISS_INDEX_CHUNKS_FILE, "wb") as f:
            pickle.dump(chunks, f)

        return index

    # Step 3: Load FAISS index from disk
    def _load_faiss_index(self, index_path):
        """
        Load a FAISS index and corresponding chunks from disk.
        """
        if not os.path.exists(index_path) or not os.path.exists(AICODER_FAISS_INDEX_CHUNKS_FILE):
            return None, None

        # Load the FAISS index
        index = faiss.read_index(index_path)

        # Load the chunks
        with open(AICODER_FAISS_INDEX_CHUNKS_FILE, "rb") as f:
            chunks = pickle.load(f)

        return index, chunks

    # Step 4: Retrieve relevant chunks and generate a response
    def _retrieve_and_generate(self, query, index, chunks, embedding_model, llm_model, tokenizer):
        """
        Retrieve relevant chunks and generate a response using the LLM.
        """
        # Embed the query
        query_embedding = embedding_model.encode([query])
        distances, indices = index.search(query_embedding, k=5)  # Retrieve top 5 chunks
        relevant_chunks = [chunks[i] for i in indices[0]]
        context = "\n".join(relevant_chunks)

        # Prepare the input for the LLM
        input_text = f"Context:\n{context}\n\nQuestion: {query}"
        inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=1024)

        # Generate the response
        outputs = llm_model.generate(
            **inputs,
            max_new_tokens=2000,  # Limit the response length
            pad_token_id=tokenizer.eos_token_id,  # Avoid warnings about padding
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response

    def retrain_aicoder(self):
        try:
            # Delete the existing index and chunks
            if os.path.exists(AICODER_FAISS_INDEX_FILE):
                os.remove(AICODER_FAISS_INDEX_FILE)
            if os.path.exists(AICODER_FAISS_INDEX_CHUNKS_FILE):
                os.remove(AICODER_FAISS_INDEX_CHUNKS_FILE)
            self._check_faiss_index()
            return True
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return False

    # Main function to run the RAG pipeline
    def ask_aicoder(self, question):
        try:
            # Step 3: Query the model
            logger.info("Generating response...")
            response = self._retrieve_and_generate(
                question, self.__index, self.__chunks, self.__embedding_model, self.__model, self.__tokenizer
            )
            logger.info(f"\nResponse:\n{response}")
            return response
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None
