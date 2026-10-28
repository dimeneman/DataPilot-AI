import os
import io
from contextlib import redirect_stdout, redirect_stderr

import requests
import pandas as pd


class ETLTools:
    def __init__(self):
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        self._dataframe_cache = {}

    def _resolve_path(self, path: str) -> str:
        """
        Convert a relative path into an absolute path
        based on the project root.
        """
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self.project_root, path))

    def _build_dataframe_profile(self, df: pd.DataFrame, file_path: str) -> str:
        """
        Build a rich text summary of a dataframe for LLM context.
        """
        lines = []
        lines.append(f"File: {file_path}")
        lines.append(f"Rows: {df.shape[0]}")
        lines.append(f"Columns: {df.shape[1]}")
        lines.append("")

        lines.append("Column Names:")
        for col in df.columns:
            lines.append(f"- {col}")

        lines.append("")
        lines.append("Data Types:")
        for col, dtype in df.dtypes.items():
            lines.append(f"- {col}: {dtype}")

        lines.append("")
        lines.append("Missing Values:")
        missing = df.isna().sum()
        missing = missing[missing > 0]

        if missing.empty:
            lines.append("- None")
        else:
            for col, count in missing.items():
                lines.append(f"- {col}: {count}")

        lines.append("")
        lines.append("Sample Rows:")
        if df.empty:
            lines.append("- DataFrame is empty.")
        else:
            lines.append(df.head(3).to_string(index=False))

        return "\n".join(lines)

    def extract_load(self, url: str, output_folder: str, format: str):
        """
        Extract data from an API, normalize it, and save it to disk.
        Supported formats: csv, json, parquet, xlsx.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "results" in data:
                records = data["results"]
            elif isinstance(data, list):
                records = data
            else:
                records = [data]

            df = pd.json_normalize(records)

            output_folder = self._resolve_path(output_folder)
            os.makedirs(output_folder, exist_ok=True)

            file_format = format.strip().lower()
            if file_format == "csv":
                filename = os.path.join(output_folder, "extracted_data.csv")
                df.to_csv(filename, index=False)

            elif file_format == "json":
                filename = os.path.join(output_folder, "extracted_data.json")
                df.to_json(filename, orient="records", lines=True, force_ascii=False)

            elif file_format == "parquet":
                filename = os.path.join(output_folder, "extracted_data.parquet")
                df.to_parquet(filename, index=False)

            elif file_format in {"xlsx", "xls", "excel"}:
                filename = os.path.join(output_folder, "extracted_data.xlsx")
                df.to_excel(filename, index=False)

            else:
                return f"Unsupported format: {format}"

            # Invalidate cache if this file is extracted again.
            self._dataframe_cache.pop(filename, None)

            return f"Data successfully extracted and saved to {filename}"

        except requests.exceptions.RequestException as e:
            return f"Failed to extract data: {e}"
        except Exception as e:
            return f"Failed to extract data: {e}"

    def transform_load_context(self, file_path: str):
        """
        Read a file and return a rich dataframe profile for LLM context.
        Supports csv, json, parquet, xlsx, xls.
        """
        try:
            resolved_path = self._resolve_path(file_path)

            if not os.path.exists(resolved_path):
                return f"File not found: {resolved_path}"

            if resolved_path in self._dataframe_cache:
                df = self._dataframe_cache[resolved_path]
            else:
                file_extension = os.path.splitext(resolved_path)[1].lower()

                if file_extension == ".csv":
                    df = pd.read_csv(resolved_path)

                elif file_extension == ".json":
                    df = pd.read_json(resolved_path, lines=True)

                elif file_extension == ".parquet":
                    df = pd.read_parquet(resolved_path)

                elif file_extension in {".xlsx", ".xls"}:
                    df = pd.read_excel(resolved_path)

                else:
                    return f"Unsupported file format: {file_extension}"

                self._dataframe_cache[resolved_path] = df

            return self._build_dataframe_profile(df, resolved_path)

        except Exception as e:
            return f"Failed to transform file: {e}"

    def execute_code(self, code: str):
        """
        Execute the provided code and return the output.
        Note: this is still powerful and should only be used with trusted agent-generated code.
        """
        try:
            stdout_buffer = io.StringIO()

            # Keep the execution context minimal but useful.
            safe_globals = {
                "__builtins__": __builtins__,
                "pd": pd,
                "os": os,
            }
            safe_locals = {}

            with redirect_stdout(stdout_buffer), redirect_stderr(stdout_buffer):
                exec(code, safe_globals, safe_locals)

            output = stdout_buffer.getvalue().strip()
            return output if output else "Code executed successfully."

        except Exception as e:
            return f"Failed to execute code: {e}"


if __name__ == "__main__":
    obj = ETLTools()

    # Example: extract fresh data first
    print(
        obj.extract_load(
            url="https://randomuser.me/api/?results=20",
            output_folder="data/extract",
            format="csv",
        )
    )

    # Then transform the file that was just created
    path = "data/extract/extracted_data.csv"
    print(obj.transform_load_context(path))