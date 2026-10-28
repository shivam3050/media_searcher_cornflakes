def mock_llm_query_understanding(raw_query: str) -> dict:
    return {
        # Query ko bas chhota (lowercase) kar diya
        "clean_text": raw_query.lower().strip(),
        # Ek dummy filter daal diya taaki requirement poori ho jaye
        "filters": {"mock_attribute": "dummy_value"} 
    }