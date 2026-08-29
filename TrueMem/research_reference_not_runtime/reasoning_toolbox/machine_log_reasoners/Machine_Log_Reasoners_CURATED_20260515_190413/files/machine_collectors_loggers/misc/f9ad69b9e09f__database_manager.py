import sqlite3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default database path in the same directory as the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'citations.db')

def connect_db(db_path=None):
    """
    Establishes a connection to the SQLite database and returns the connection and cursor.
    
    Args:
        db_path (str, optional): Path to the database file. Defaults to DATABASE_PATH.
        
    Returns:
        tuple: (connection, cursor) or (None, None) if connection fails
    """
    try:
        # Use provided path or default
        path = db_path or DATABASE_PATH
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        logging.info(f"Connected to database at {path}")
        return conn, cur
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None, None

def create_tables(cur):
    """
    Creates the necessary tables in the database if they do not exist.
    
    Args:
        cur: Database cursor
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create main citations table with expanded fields
        cur.execute('''
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT,
                title TEXT,
                year TEXT,
                journal TEXT,
                publisher TEXT,
                volume TEXT,
                issue TEXT,
                pages TEXT,
                conference TEXT,
                url TEXT,
                access_date TEXT,
                location TEXT,
                category TEXT,
                standardized_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create a search index table for faster lookups
        cur.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS citation_index 
            USING fts5(
                id, author, title, year, journal, publisher, 
                content='citations', content_rowid='id'
            )
        ''')
        
        # Create trigger to update the search index when citations are inserted
        cur.execute('''
            CREATE TRIGGER IF NOT EXISTS citations_ai AFTER INSERT ON citations BEGIN
                INSERT INTO citation_index(id, author, title, year, journal, publisher)
                VALUES (new.id, new.author, new.title, new.year, new.journal, new.publisher);
            END;
        ''')
        
        logging.info("Tables created successfully or already exist.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Error creating tables: {e}")
        return False

def create_citation(cur, conn, entities, category=None, standardized_text=None):
    """
    Inserts a new citation into the database.
    
    Args:
        cur: Database cursor
        conn: Database connection
        entities (dict): Dictionary of citation entities
        category (str, optional): Citation category
        standardized_text (str, optional): Standardized citation text
        
    Returns:
        int: Citation ID if successful, None otherwise
    """
    try:
        # Extract all possible fields from entities
        author = entities.get('author')
        title = entities.get('title')
        year = entities.get('year')
        journal = entities.get('journal')
        publisher = entities.get('publisher')
        volume = entities.get('volume')
        issue = entities.get('issue')
        pages = entities.get('pages')
        conference = entities.get('conference')
        url = entities.get('url')
        access_date = entities.get('access_date')
        location = entities.get('location')
        
        # Use provided category or default to unknown
        cat = category or entities.get('category', 'unknown')
        
        # Use provided standardized text or empty string
        std_text = standardized_text or ''
        
        cur.execute('''
            INSERT INTO citations (
                author, title, year, journal, publisher, 
                volume, issue, pages, conference, url, 
                access_date, location, category, standardized_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            author, title, year, journal, publisher,
            volume, issue, pages, conference, url,
            access_date, location, cat, std_text
        ))
        
        conn.commit()
        citation_id = cur.lastrowid
        logging.info(f"Citation inserted with ID: {citation_id}")
        return citation_id
    except sqlite3.Error as e:
        logging.error(f"Error inserting citation: {e}")
        return None

def search_citations(cur, search_term):
    """
    Searches for citations matching the search term.
    
    Args:
        cur: Database cursor
        search_term (str): Term to search for
        
    Returns:
        list: List of matching citation dictionaries
    """
    try:
        # Use FTS5 for efficient full-text search
        cur.execute('''
            SELECT c.* FROM citations c
            JOIN citation_index i ON c.id = i.id
            WHERE citation_index MATCH ?
            ORDER BY c.year DESC
        ''', (search_term,))
        
        # Convert results to list of dictionaries
        columns = [col[0] for col in cur.description]
        results = [dict(zip(columns, row)) for row in cur.fetchall()]
        
        logging.info(f"Found {len(results)} citations matching '{search_term}'")
        return results
    except sqlite3.Error as e:
        logging.error(f"Error searching citations: {e}")
        return []

def get_citation_by_id(cur, citation_id):
    """
    Retrieves a citation by its ID.
    
    Args:
        cur: Database cursor
        citation_id (int): Citation ID
        
    Returns:
        dict: Citation data or None if not found
    """
    try:
        cur.execute('SELECT * FROM citations WHERE id = ?', (citation_id,))
        row = cur.fetchone()
        
        if row:
            columns = [col[0] for col in cur.description]
            result = dict(zip(columns, row))
            return result
        else:
            logging.warning(f"No citation found with ID: {citation_id}")
            return None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving citation: {e}")
        return None

if __name__ == "__main__":
    # Example Usage
    conn, cur = connect_db()
    if conn and cur:
        # Create tables
        create_tables(cur)
        
        # Example citation entities
        entities = {
            "author": "Doe, J. and Smith, A.",
            "title": "The Impact of AI on Society",
            "year": "2022",
            "journal": "Journal of Artificial Intelligence",
            "volume": "45",
            "issue": "2",
            "pages": "123-145"
        }
        
        # Insert citation
        citation_id = create_citation(cur, conn, entities, "article", 
                                     "Doe, J. and Smith, A. (2022). The Impact of AI on Society. Journal of Artificial Intelligence, 45(2), 123-145.")
        print(f"Inserted Citation ID: {citation_id}")
        
        # Search for citations
        if citation_id:
            results = search_citations(cur, "AI")
            print(f"Search Results: {results}")
            
            # Get citation by ID
            citation = get_citation_by_id(cur, citation_id)
            print(f"Retrieved Citation: {citation}")
        
        # Close connection
        cur.close()
        conn.close()
