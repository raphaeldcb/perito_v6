"""Data anonymization module.

This module anonymizes sensitive data in SQL dumps using Faker,
making production data safe for use in staging environments.
"""

import re
import sys
from random import randint, uniform
from typing import Optional
from pathlib import Path

try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False
    Faker = None  # type: ignore


class SQLAnonymizer:
    """Anonymizes sensitive data in SQL dumps."""

    def __init__(self, locale: str = "pt_BR"):
        """Initialize anonymizer with Faker instance.

        Args:
            locale: Locale for Faker (default: pt_BR for Brazilian data)

        Raises:
            ImportError: If faker package is not installed
        """
        if not HAS_FAKER or Faker is None:
            raise ImportError(
                "faker package not found. Install with: pip install faker==19.3.0"
            )
        self.fake = Faker(locale)
        self.cpf_map: dict[str, str] = {}
        self.cnpj_map: dict[str, str] = {}
        self.name_map: dict[str, str] = {}
        self.email_map: dict[str, str] = {}
        self.phone_map: dict[str, str] = {}

    def generate_fake_cpf(self) -> str:
        """Generate a fake CPF (11 digits).

        Returns:
            Random 11-digit string formatted as CPF
        """
        return f"{randint(10000000000, 99999999999)}"

    def generate_fake_cnpj(self) -> str:
        """Generate a fake CNPJ (14 digits).

        Returns:
            Random 14-digit string formatted as CNPJ
        """
        return f"{randint(10000000000000, 99999999999999)}"

    def anonymize_cpf(self, cpf: str) -> str:
        """Anonymize CPF value.

        Uses consistent mapping to replace same CPF with same fake value.

        Args:
            cpf: Original CPF string

        Returns:
            Anonymized CPF (fake but consistent)
        """
        if cpf not in self.cpf_map:
            self.cpf_map[cpf] = self.generate_fake_cpf()
        return self.cpf_map[cpf]

    def anonymize_cnpj(self, cnpj: str) -> str:
        """Anonymize CNPJ value.

        Uses consistent mapping to replace same CNPJ with same fake value.

        Args:
            cnpj: Original CNPJ string

        Returns:
            Anonymized CNPJ (fake but consistent)
        """
        if cnpj not in self.cnpj_map:
            self.cnpj_map[cnpj] = self.generate_fake_cnpj()
        return self.cnpj_map[cnpj]

    def anonymize_name(self, name: str) -> str:
        """Anonymize person/company name.

        Args:
            name: Original name string

        Returns:
            Anonymized name
        """
        if name not in self.name_map:
            self.name_map[name] = self.fake.name()
        return self.name_map[name]

    def anonymize_email(self, email: str) -> str:
        """Anonymize email address.

        Args:
            email: Original email string

        Returns:
            Anonymized email
        """
        if email not in self.email_map:
            self.email_map[email] = self.fake.email()
        return self.email_map[email]

    def anonymize_phone(self, phone: str) -> str:
        """Anonymize phone number.

        Args:
            phone: Original phone string

        Returns:
            Anonymized phone (Brazilian format)
        """
        if phone not in self.phone_map:
            # Generate fake Brazilian phone
            self.phone_map[phone] = f"{randint(11, 99)}{randint(90000, 99999)}{randint(0, 9999):04d}"
        return self.phone_map[phone]

    def anonymize_monetary_value(self, value: float) -> float:
        """Anonymize monetary value by reducing 10-50% randomly.

        Preserves magnitude for realistic range but prevents exact value matching.

        Args:
            value: Original monetary value

        Returns:
            Reduced value (10-50% less)
        """
        if value <= 0:
            return value
        reduction = uniform(0.1, 0.5)
        return round(value * (1 - reduction), 2)

    def anonymize_sql_value(self, value: str, field_name: str) -> str:
        """Anonymize a single SQL value based on field name detection.

        Args:
            value: Original value string (may include quotes)
            field_name: Name of the database field

        Returns:
            Anonymized value string
        """
        # Remove quotes if present
        quoted = value.startswith("'") and value.endswith("'")
        unquoted = value.strip("'")

        field_lower = field_name.lower()
        anonymized = None

        # Detect field type and anonymize
        if "cpf" in field_lower:
            if unquoted.isdigit() and len(unquoted) == 11:
                anonymized = self.anonymize_cpf(unquoted)
        elif "cnpj" in field_lower:
            if unquoted.isdigit() and len(unquoted) == 14:
                anonymized = self.anonymize_cnpj(unquoted)
        elif "email" in field_lower or "mail" in field_lower:
            anonymized = self.anonymize_email(unquoted)
        elif "phone" in field_lower or "celular" in field_lower or "telefone" in field_lower:
            anonymized = self.anonymize_phone(unquoted)
        elif "nome" in field_lower or "name" in field_lower:
            if not any(char.isdigit() for char in unquoted[:3]):  # Don't anonymize if starts with numbers
                anonymized = self.anonymize_name(unquoted)
        elif "valor" in field_lower or "amount" in field_lower or "price" in field_lower:
            try:
                numeric_val = float(unquoted)
                anonymized = str(self.anonymize_monetary_value(numeric_val))
            except ValueError:
                pass

        if anonymized:
            return f"'{anonymized}'" if quoted else anonymized
        return value

    def anonymize_insert_statement(self, statement: str) -> str:
        """Anonymize an INSERT statement.

        Args:
            statement: SQL INSERT statement

        Returns:
            Anonymized INSERT statement
        """
        # Extract table name and columns
        match = re.match(
            r"INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\);?",
            statement,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return statement

        table_name = match.group(1)
        columns_str = match.group(2)
        values_str = match.group(3)

        # Parse columns
        columns = [col.strip() for col in columns_str.split(",")]

        # Parse values - handle quoted strings carefully
        values = []
        current_value = ""
        in_quotes = False

        for char in values_str:
            if char == "'" and (not current_value or current_value[-1] != "\\"):
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                values.append(current_value.strip())
                current_value = ""
                continue
            current_value += char

        if current_value.strip():
            values.append(current_value.strip())

        # Anonymize values
        anonymized_values = []
        for i, value in enumerate(values):
            if i < len(columns):
                anonymized_value = self.anonymize_sql_value(value, columns[i])
                anonymized_values.append(anonymized_value)
            else:
                anonymized_values.append(value)

        # Reconstruct INSERT statement
        return f"INSERT INTO {table_name} ({columns_str}) VALUES ({', '.join(anonymized_values)});"

    def anonymize_sql(self, sql_content: str) -> str:
        """Anonymize entire SQL dump.

        Args:
            sql_content: SQL dump content

        Returns:
            Anonymized SQL content
        """
        # First, join multiline INSERT statements
        # Convert to single line for easier parsing
        content = sql_content

        # Replace multiple spaces/newlines in INSERT statements with single space
        insert_pattern = r"INSERT\s+INTO\s+\w+\s*\([^)]+\)\s*VALUES\s*\([^)]+\);?"

        def process_insert(match):
            insert_stmt = match.group(0)
            # Remove all newlines and extra spaces within the statement
            insert_stmt = " ".join(insert_stmt.split())
            return self.anonymize_insert_statement(insert_stmt)

        # Process INSERT statements
        result = re.sub(insert_pattern, process_insert, content, flags=re.IGNORECASE | re.DOTALL)

        return result


def anonymize_sql(sql_content: str, locale: str = "pt_BR") -> str:
    """Anonymize SQL content using Faker.

    Convenience function for direct anonymization without creating anonymizer instance.

    Args:
        sql_content: SQL dump content
        locale: Faker locale (default: pt_BR)

    Returns:
        Anonymized SQL content
    """
    anonymizer = SQLAnonymizer(locale=locale)
    return anonymizer.anonymize_sql(sql_content)


def anonymize_sql_file(
    input_file: str,
    output_file: str,
    locale: str = "pt_BR",
) -> bool:
    """Anonymize SQL file and write to output.

    Args:
        input_file: Path to input SQL file
        output_file: Path to output anonymized SQL file
        locale: Faker locale (default: pt_BR)

    Returns:
        True if successful, False otherwise

    Raises:
        FileNotFoundError: If input file not found
        IOError: If unable to write output file
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Read input
    with open(input_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Anonymize
    anonymized_content = anonymize_sql(sql_content, locale=locale)

    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(anonymized_content)

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Anonymize SQL dump")
    parser.add_argument("--input", required=True, help="Input SQL file")
    parser.add_argument("--output", required=True, help="Output SQL file")
    parser.add_argument("--locale", default="pt_BR", help="Faker locale")

    args = parser.parse_args()

    try:
        anonymize_sql_file(
            input_file=args.input,
            output_file=args.output,
            locale=args.locale,
        )
        print(f"Anonymization successful: {args.output}")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
