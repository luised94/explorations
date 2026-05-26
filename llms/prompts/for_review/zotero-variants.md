## **Reusable Prompt for Writing JavaScript Code for Zotero Console**

**Prompt Template:**

```
text
```

``You are an expert JavaScript developer with extensive experience in Zotero plugin and console development. Write efficient, well-structured, and optimized JavaScript code that conforms to Zotero's coding guidelines. The code should be: 1. **Zotero-Specific**: - Use Zotero's JavaScript API (e.g., `Zotero.Items`, `Zotero.File`, etc.). - Follow Zotero's coding conventions (e.g., camelCase for variables, tabs for indentation). 2. **Efficient and Scalable**: - Use batch processing for large datasets when applicable. - Include delays or asynchronous handling to prevent UI freezing. 3. **Readable and Debuggable**: - Include detailed debug messages using `Zotero.debug()` for progress tracking and error reporting. - Ensure clear separation of logic into reusable functions when appropriate. 4. **Safe and Testable**: - Include a dry-run mode to preview changes without modifying data. - Provide options to limit operations (e.g., process only a subset of items). Here is an example of the desired style and structure: [Insert your current script here as a reference] Based on this style, write a script that [describe the task or functionality you want, e.g., "updates attachment paths in the Zotero database"]. Ensure the script includes: - A dry-run option. - Debug messages for key steps. - Error handling for missing files or invalid inputs. - Batch processing if the operation involves many items. The output should be ready to run in Zotero's JavaScript console (Tools  Developer  Run JavaScript).``

## **Example Prompt Using Your Script as Reference**

``You are an expert JavaScript developer with extensive experience in Zotero plugin and console development. Write efficient, well-structured, and optimized JavaScript code that conforms to Zotero's coding guidelines. The code should: 1. Use Zotero's API (e.g., `Zotero.Items`, `Zotero.File`) and follow its coding conventions (camelCase variables, tabs for indentation). 2. Include a dry-run mode to preview changes without modifying data. 3. Process items in batches with delays to prevent UI freezing. 4. Output debug messages using `Zotero.debug()` for progress tracking and error reporting. 5. Handle errors gracefully (e.g., missing files or invalid paths). 6. Allow limiting operations to a subset of items. Here is an example of the desired style and structure:``

{{example}}

`Based on this style, write a script that updates all notes in the library by appending a timestamp indicating when they were last modified. The script should include: - A dry-run mode. - Debug messages at key steps. - Error handling for invalid notes or missing fields. - Batch processing with delays if there are many notes. The output should be ready to run in Zotero's JavaScript console.`
