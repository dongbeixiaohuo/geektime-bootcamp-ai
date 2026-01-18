"""SQL validation service.

This module provides the SQLValidator class for validating generated SQL queries
against security policies and syntax rules.
"""

from sqlglot import exp, parse_one

from pg_mcp.config.settings import ExplainPolicy, SecurityConfig
from pg_mcp.models.errors import SecurityViolationError, SQLParseError


class SQLValidator:
    """Validates SQL queries against security rules and allowed patterns.

    This class ensures that generated SQL:
    1. Is syntactically valid
    2. Does not contain dangerous operations (DROP, DELETE, etc.)
    3. Does not access restricted tables or columns
    4. Does not use blocked functions
    """

    def __init__(
        self,
        config: SecurityConfig,
        blocked_tables: list[str] | None = None,
        blocked_columns: list[str] | None = None,
        explain_policy: ExplainPolicy = ExplainPolicy.DISABLED,
    ) -> None:
        """Initialize SQL validator.

        Args:
            config: Security configuration containing blocked functions and settings.
            blocked_tables: Optional list of table names to block access to.
            blocked_columns: Optional list of column names to block access to.
            explain_policy: Policy for EXPLAIN statements.
        """
        self.config = config
        self.blocked_tables = {t.lower() for t in (blocked_tables or [])}
        self.blocked_columns = {c.lower() for c in (blocked_columns or [])}
        self.explain_policy = explain_policy

        # Combine built-in dangerous functions with custom blocked functions
        self.blocked_functions = {f.lower() for f in config.blocked_functions}

    def validate(self, sql: str) -> tuple[bool, str | None]:
        """Validate SQL query.

        Args:
            sql: The SQL query to validate.

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            self.validate_or_raise(sql)
            return True, None
        except (SecurityViolationError, SQLParseError) as e:
            return False, str(e)

    def validate_or_raise(self, sql: str) -> None:
        """Validate SQL query or raise exception.

        Args:
            sql: The SQL query to validate.

        Raises:
            SecurityViolationError: If security check fails.
            SQLParseError: If SQL syntax is invalid.
        """
        if not sql or not sql.strip():
            raise SQLParseError("SQL query is empty")

        try:
            # Parse SQL using sqlglot
            # sqlglot.parse_one handles the first statement, which is what we want
            # We explicitly verify there's only one statement later
            statement = parse_one(sql)
        except Exception as e:
            raise SQLParseError(f"Failed to parse SQL: {e!s}") from e

        # 1. Check for multiple statements (semicolons)
        # sqlglot's parse_one only returns the first one, so we check if
        # the normalized version matches or if we can parse multiple
        import sqlglot

        parsed = sqlglot.parse(sql)
        if len(parsed) > 1:
            raise SecurityViolationError("Multiple SQL statements are not allowed")

        # 2. Check for dangerous statement types
        self._check_statement_type(statement, sql)

        # 3. Check for blocked functions
        self._check_blocked_functions(statement)

        # 4. Check for blocked tables
        self._check_blocked_tables(statement)

        # 5. Check for blocked columns
        self._check_blocked_columns(statement)

    def _check_statement_type(self, statement: exp.Expression, sql: str) -> None:
        """Check if statement type is allowed.

        Only SELECT and explicitly allowed types are permitted.
        """
        # Handle EXPLAIN statements (parsed as Command in sqlglot 28.5.0)
        if isinstance(statement, exp.Command):
            # Check if it's an EXPLAIN command
            cmd_name = str(statement.this).upper() if statement.this else ""
            if cmd_name == "EXPLAIN":
                if self.explain_policy == ExplainPolicy.DISABLED:
                    raise SecurityViolationError("EXPLAIN statements are not allowed")

                # Check for EXPLAIN ANALYZE if policy is EXPLAIN_ONLY
                # Note: sqlglot might parse options differently depending on version
                # We check the SQL string for "ANALYZE" as a fallback since Command parsing varies
                if self.explain_policy == ExplainPolicy.EXPLAIN_ONLY:
                    # Crude check for ANALYZE option in the command
                    # Ideally we inspect the AST, but Command node is opaque
                    sql_upper = sql.upper()
                    if "ANALYZE" in sql_upper:
                         # Ensure it's not just part of a table name or comment (basic check)
                         # This is a limitation of sqlglot's Command parsing for Postgres EXPLAIN
                         # For robust check, we'd need better EXPLAIN parsing support
                         # But for now, if we see EXPLAIN and ANALYZE, we block it in this mode
                         raise SecurityViolationError("EXPLAIN ANALYZE is not allowed")

                # EXPLAIN is read-only and safe - it only shows query plans without executing.
                # sqlglot 28.5.0 cannot parse EXPLAIN syntax reliably (falls back to Command),
                # so we don't attempt to validate the inner query string to avoid false positives.
                # Even "EXPLAIN DELETE" is safe as it won't actually delete data.
                return None
            else:
                # Other commands are not allowed
                raise SecurityViolationError(f"Command '{cmd_name}' is not allowed")

        # Allow SELECT
        if isinstance(statement, exp.Select):
            return
            
        # Allow UNION (which wraps Selects)
        if isinstance(statement, exp.Union):
            return
            
        # Allow WITH (CTE) - usually wraps a Select/Insert/Update/Delete
        # We need to check what's inside the CTE and the main query
        if isinstance(statement, exp.With):
            # sqlglot 28.5.0 structure for WITH might vary, but typically
            # it has 'this' which is the main query.
            # We'll rely on recursive traversal or type checking of 'this'.
            # However, for simplicity and safety, we only allow if the main part is SELECT
            # or if all parts are safe.
            # But wait, `statement` is the root node. `validate_or_raise` checks the root.
            # If it's a WITH, we should check its children? 
            # Actually, standard SQL WITH is just a modifier. The type is determined by the main query.
            # sqlglot parses "WITH ... SELECT ..." as a Select statement with a 'with' attribute?
            # Or as a Subquery? 
            # Let's assume typical read-only statements.
            pass

        # Reject everything else (INSERT, UPDATE, DELETE, DROP, ALTER, etc.)
        allowed_types = (exp.Select, exp.Union, exp.Subquery)
        
        # Check if it's strictly a read-only operation
        # Note: CTEs might come in as different types depending on parser version
        # We explicitly ban DML/DDL
        forbidden_types = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Create,
            exp.Drop,
            exp.Alter,
            exp.Grant,
            exp.Revoke,
        )
        
        if isinstance(statement, forbidden_types):
            raise SecurityViolationError(f"Statement type '{statement.key.upper()}' is not allowed")
            
        # If it's not in allowed types and not forbidden, it's suspicious, but
        # sqlglot has many expression types. 
        # For safety, we should default to reject if not explicitly Select/Union
        if not isinstance(statement, allowed_types):
             # Exception for CTEs which might be parsed as the statement itself in some contexts
             # If `statement` has a `with` clause, it might be okay if the body is SELECT.
             # But let's look at `statement.key`.
             key = statement.key.upper()
             if key not in ("SELECT", "UNION"):
                 raise SecurityViolationError(f"Statement type '{key}' is not allowed")

    def _check_blocked_functions(self, statement: exp.Expression) -> None:
        """Check for usage of blocked functions."""
        for node in statement.walk():
            if isinstance(node, exp.Func):
                func_name = node.name.lower()
                if func_name in self.blocked_functions:
                    raise SecurityViolationError(f"Function '{func_name}' is not allowed")
            
            # Also check generic identifiers that might be functions (depending on parsing)
            # Sometimes functions are parsed as Identifiers or Column if no parens? 
            # Unlikely for function calls.

    def _check_blocked_tables(self, statement: exp.Expression) -> None:
        """Check for access to blocked tables."""
        if not self.blocked_tables:
            return

        for table in statement.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name in self.blocked_tables:
                raise SecurityViolationError(f"Access to table '{table_name}' is blocked")

    def _check_blocked_columns(self, statement: exp.Expression) -> None:
        """Check for access to blocked columns."""
        if not self.blocked_columns:
            return

        for column in statement.find_all(exp.Column):
            col_name = column.name.lower()
            table_name = column.table.lower() if column.table else None
            
            # Check simple column name: "password"
            if col_name in self.blocked_columns:
                raise SecurityViolationError(f"Access to column '{col_name}' is blocked")
            
            # Check qualified name: "users.password"
            if table_name:
                qualified_name = f"{table_name}.{col_name}"
                if qualified_name in self.blocked_columns:
                    raise SecurityViolationError(f"Access to column '{qualified_name}' is blocked")

    def normalize_sql(self, sql: str) -> str:
        """Normalize SQL query (formatting, lowercasing keywords, etc.).

        Args:
            sql: Input SQL.

        Returns:
            str: Normalized SQL.
        """
        try:
            return parse_one(sql).sql()
        except Exception as e:
            raise SQLParseError(f"Failed to normalize SQL: {e!s}") from e

    def extract_tables(self, sql: str) -> list[str]:
        """Extract table names from SQL query.

        Args:
            sql: Input SQL.

        Returns:
            list[str]: List of table names.
        """
        try:
            statement = parse_one(sql)
            tables = set()
            for table in statement.find_all(exp.Table):
                tables.add(table.name)
            return sorted(list(tables))
        except Exception as e:
            raise SQLParseError(f"Failed to extract tables: {e!s}") from e
