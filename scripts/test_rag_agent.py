"""
Testing script for RAG Agent
Tests storing candidate data and retrieving relevant information
"""

import argparse
from agents.rag import RAGAgent
from agents.rag.models import StoreRequest, QueryRequest


# Sample candidate data for testing
TEST_CANDIDATES = [
    {
        "name": "John Anderson",
        "content": """
        John Anderson is a Senior Backend Developer with 6 years of experience.
        
        His core skills include Python, FastAPI, Django, and PostgreSQL.
        He has designed scalable REST APIs for SaaS platforms.
        Experienced with Docker, CI/CD pipelines, and AWS deployment.
        """
    },
    {
        "name": "Sarah Chen",
        "content": """
        Sarah Chen is a Full Stack Engineer with 4 years of experience.
        
        Frontend skills: React, TypeScript, Tailwind CSS, Next.js
        Backend skills: Python, FastAPI, Node.js
        Database: PostgreSQL, MongoDB
        DevOps: Docker, Kubernetes, GitHub Actions
        """
    }
]

# Test queries
TEST_QUERIES = [
    "Who has experience with Python and FastAPI?",
    "Which candidate knows React and TypeScript?",
    "Who has data engineering experience?",
    "Find someone with Docker and Kubernetes knowledge",
    "Who can work with PostgreSQL and AWS?"
]


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_store_candidates():
    """Test storing candidate data"""
    print_section("TESTING: Store Candidate Data")
    
    agent = RAGAgent()
    
    for candidate in TEST_CANDIDATES:
        print(f"Storing: {candidate['name']}")
        req = StoreRequest(
            name=candidate['name'],
            content=candidate['content']
        )
        result = agent.store(req)
        print(f"  ✓ Status: {result.success}")
        print(f"  ✓ Chunks created: {result.stored_chunks}")
        if result.message:
            print(f"  ℹ Message: {result.message}")
        print()


def format_result(result_item, index):
    """Format a single result item for display"""
    output = f"\n  {index}. Name: {result_item.get('name', 'Unknown')}\n"
    
    if "candidate_id" in result_item:
        output += f"     Candidate ID: {result_item.get('candidate_id', 'N/A')}\n"
        
    if 'average_similarity' in result_item:
        output += f"     AVG Similarity: {result_item.get('average_similarity', 'N/A')}\n"
    
    if 'chunk_matches' in result_item:
        output += f"     Chunk matches: {result_item.get('chunk_matches', 'N/A')}\n"
    
    if 'chunks' in result_item:
        output += f"     Chunks: {result_item.get('chunks', 'N/A')}\n"
    
    return output


def test_retrieve_candidates(custom_queries=None):
    """Test retrieving candidate data"""
    print_section("TESTING: Retrieve Candidate Data")
    
    agent = RAGAgent()
    queries = custom_queries if custom_queries else TEST_QUERIES
    
    for query in queries:
        print(f"Query: '{query}'")
        req = QueryRequest(query=query, top_k=10)
        result = agent.retrieve(req)
        
        print(f"  ✓ Status: {result.success}")
        
        if result.success and result.results:
            print(f"  ✓ Found {len(result.results)} result(s):")
            for idx, res in enumerate(result.results, 1):
                print(format_result(res, idx))
        else:
            print(f"  ✗ Error: {result.message}")
        print()


def test_end_to_end():
    """Complete end-to-end test: store then retrieve"""
    print_section("TESTING: End-to-End Flow")
    
    agent = RAGAgent()
    
    # Step 1: Store all candidates
    print("Step 1: Storing all candidates...")
    for candidate in TEST_CANDIDATES:
        req = StoreRequest(
            name=candidate['name'],
            content=candidate['content']
        )
        result = agent.store(req)
        status = "✓" if result.success else "✗"
        print(f"  {status} {candidate['name']}")
    
    print("\nStep 2: Running queries to retrieve candidates...")
    for query in TEST_QUERIES[:3]:  # Test only first 3 queries
        req = QueryRequest(query=query, top_k=2)
        result = agent.retrieve(req)
        status = "✓" if result.success else "✗"
        print(f"  {status} '{query}'")
        if result.success and result.results:
            for res in result.results:
                print(f"     - {res.get('name', 'Unknown')}")


def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(
        description="RAG Agent Testing Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_rag_agent.py store                    # Store all test candidates
  python scripts/test_rag_agent.py retrieve                 # Retrieve using default queries
  python scripts/test_rag_agent.py retrieve -q "Python skills"    # Custom query
  python scripts/test_rag_agent.py retrieve -q "Python" -q "React" # Multiple queries
  python scripts/test_rag_agent.py all                      # Run all tests
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Store command
    subparsers.add_parser("store", help="Store test candidate data")
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser("retrieve", help="Retrieve candidate data")
    retrieve_parser.add_argument(
        "-q", "--query",
        action="append",
        dest="queries",
        help="Custom query (can be used multiple times)"
    )
    retrieve_parser.add_argument(
        "-k", "--top-k",
        type=int,
        default=3,
        help="Number of top results to return (default: 3)"
    )
    
    # All command
    subparsers.add_parser("all", help="Run all tests")
    
    args = parser.parse_args()
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  RAG Agent Testing Suite".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        if args.command == "store":
            test_store_candidates()
        elif args.command == "retrieve":
            # If custom queries provided, use them
            if args.queries:
                test_retrieve_candidates(custom_queries=args.queries)
            else:
                test_retrieve_candidates()
        elif args.command == "all":
            test_store_candidates()
            test_retrieve_candidates()
            test_end_to_end()
        else:
            # Default behavior if no command specified
            test_store_candidates()
            test_retrieve_candidates()
        
        print_section("All Tests Completed ✓")
        
    except Exception as e:
        print_section(f"Test Failed ✗")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
