`def achieve_simplicity_and_elegance(design_goals): # Identify the axes or dimensions of the design goals design_axes = identify_design_axes(design_goals) # Find the "super idea" that solves the axes simultaneously super_idea = find_super_idea(design_axes) # Evaluate the simplicity and elegance of the super idea simplicity_score, elegance_score = evaluate_simplicity_and_elegance(super_idea) # Return the super idea and its scores return super_idea, simplicity_score, elegance_score def identify_design_axes(design_goals): # Analyze the design goals and identify the key axes or dimensions axes = [] for goal in design_goals: # Extract the underlying axes or dimensions from each design goal goal_axes = extract_axes(goal) axes.extend(goal_axes) # Remove duplicates and consolidate related axes consolidated_axes = consolidate_axes(axes) return consolidated_axes def find_super_idea(design_axes): # Generate potential ideas that address the design axes potential_ideas = generate_ideas(design_axes) # Evaluate each idea against the design axes evaluated_ideas = evaluate_ideas(potential_ideas, design_axes) # Select the idea that best solves the axes simultaneously super_idea = select_best_idea(evaluated_ideas) return super_idea def evaluate_simplicity_and_elegance(idea): # Assess the simplicity of the idea simplicity_score = assess_simplicity(idea) # Assess the elegance of the idea elegance_score = assess_elegance(idea) return simplicity_score, elegance_score`
---
def analyze_and_refactor_code(code, <programming_language>):

code_sections = identify_code_sections(code)

conceptual_summary = []

feedback_suggestions = []

for section in code_sections:

section_purpose = analyze_section_purpose(section)

conceptual_summary.append(section_purpose)

section_feedback = provide_section_feedback(section)

feedback_suggestions.append(section_feedback)

refactored_code = reorganize_code(code_sections, conceptual_summary, feedback_suggestions)

refactored_code = add_command_line_arguments(refactored_code)

refactored_code = create_section_functions(refactored_code)

refactored_code = create_main_function(refactored_code)

refactored_code = add_input_validation(refactored_code)

refactored_code = apply_best_practices(refactored_code)

return refactored_code

Output the <thoughts> step by step.

Referred in [#Main Workspace Note](zotero://note/u/EZ49J5CV/?ignore=1&line=-1)
---
def analyze_and_refactor_code(code, R):  
environment(no_hallucinate)

code_sections = conceptual_breakdown_into_sections(code)

conceptual_summary = [] feedback_suggestions = []

for section in code_sections: section_purpose = analyze_section_purpose(section) conceptual_summary.append(section_purpose) section_feedback = provide_section_feedback(section) feedback_suggestions.append(section_feedback) refactored_code = reorganize_code(code_sections, conceptual_summary, feedback_suggestions) refactored_code = create_section_functions(refactored_code) refactored_code = add_input_validation(refactored_code) refactored_code = apply_best_practices(refactored_code) return refactored_code
---
`def apply_persona(task):`

`result = perform_task(task) return format_output(result)`

`def apply_thinking_and_reasoning(task):`

`reasoning = analyze_task(task) return format_reasoning(reasoning)`

`def generate_output(task, reasoning):`

`kanban = create_kanban_board(task) problem = define_problem(task) rca = perform_root_cause_analysis(problem) whys = iterate_four_whys(rca)`

`output = f""" Kanban: {kanban} Problem: {problem} Root Cause Analysis (RCA): {rca} 4 Whys: {whys} """ return output`

`def main(task): persona_result = apply_persona(task) reasoning = apply_thinking_and_reasoning(task) output = generate_output(task, reasoning) return f""" Persona Result: {persona_result} Reasoning: {reasoning} Output: {output} """`

`return main`
---
`def conceptual_understanding(code): # Divide the code into sections code_sections = divide_code_into_sections(code) # Identify the main purpose of each section section_purposes = identify_section_purposes(code_sections) # Analyze the logical flow and dependencies between sections logical_flow, dependencies = analyze_logical_flow_and_dependencies(code_sections) # Recognize assumptions and constraints assumptions, constraints = recognize_assumptions_and_constraints(code_sections) # Combine the conceptual understanding components conceptual_understanding = { 'section_purposes': section_purposes, 'logical_flow': logical_flow, 'dependencies': dependencies, 'assumptions': assumptions, 'constraints': constraints } return conceptual_understanding def divide_code_into_sections(code): # Divide the code into logical sections based on functionality or structure sections = [] # Implementation logic to divide the code into sections return sections def identify_section_purposes(code_sections): purposes = [] for section in code_sections: # Analyze each section to identify its main purpose purpose = identify_purpose(section) purposes.append(purpose) return purposes def analyze_logical_flow_and_dependencies(code_sections): # Analyze the logical flow of the code sections logical_flow = determine_logical_flow(code_sections) # Identify dependencies between code sections dependencies = identify_dependencies(code_sections) return logical_flow, dependencies def recognize_assumptions_and_constraints(code_sections): assumptions = [] constraints = [] for section in code_sections: # Identify assumptions made in each code section section_assumptions = identify_assumptions(section) assumptions.extend(section_assumptions) # Identify constraints present in each code section section_constraints = identify_constraints(section) constraints.extend(section_constraints) return assumptions, constraints`
---
`def connect_concepts_isomorphism(concept1, concept2): shared_concepts = find_shared_concepts(concept1, concept2) shared_dimensions = find_shared_dimensions(concept1, concept2) logical_bridges = create_logical_bridges(concept1, concept2, shared_dimensions) anchor_points = identify_anchor_points(concept1, concept2) connection_strength = evaluate_connection_strength(shared_concepts, shared_dimensions, logical_bridges, anchor_points) isomorphism = { 'input': (concept1, concept2), 'output': connection_strength } return isomorphism`
---
`def developer_experience_function(code, documentation): # Add motivation and explanation motivated_code = add_motivation(code) # Choose descriptive and intuitive names named_code = choose_names(motivated_code) # Apply snake_case naming convention snake_case_code = apply_snake_case(named_code) # Avoid abbreviations and add units or qualifiers unabbreviated_code = avoid_abbreviations(snake_case_code) # Align related names aligned_code = align_related_names(unabbreviated_code) # Avoid overloading names unambiguous_code = avoid_name_overloading(aligned_code) # Consider external usage of names externally_usable_code = consider_external_usage(unambiguous_code) # Prefix helper function and callback names prefixed_code = prefix_helper_names(externally_usable_code) # Place callbacks last in parameter list callback_ordered_code = order_callbacks(prefixed_code) # Order code for readability ordered_code = order_for_readability(callback_ordered_code) # Add comments for why and how commented_code = add_comments(ordered_code, documentation) # Return the final code return commented_code def add_motivation(code): # Add motivation and explanation to the code motivated_code = [] for line in code: # Add motivation and explanation for each line motivated_line = add_motivation_to_line(line) motivated_code.append(motivated_line) return motivated_code def choose_names(code): # Choose descriptive and intuitive names for functions, variables, and files named_code = [] for line in code: # Choose descriptive and intuitive names for each line named_line = choose_names_for_line(line) named_code.append(named_line) return named_code def apply_snake_case(code): # Apply snake_case naming convention to the code snake_case_code = [] for line in code: # Apply snake_case to each line snake_case_line = convert_to_snake_case(line) snake_case_code.append(snake_case_line) return snake_case_code def avoid_abbreviations(code): # Avoid abbreviations and add units or qualifiers to variable names unabbreviated_code = [] for line in code: # Avoid abbreviations and add units or qualifiers for each line unabbreviated_line = expand_abbreviations(line) unabbreviated_code.append(unabbreviated_line) return unabbreviated_code def align_related_names(code): # Align related names to have the same number of characters aligned_code = [] for line in code: # Align related names for each line aligned_line = align_names(line) aligned_code.append(aligned_line) return aligned_code def avoid_name_overloading(code): # Avoid overloading names with multiple context-dependent meanings unambiguous_code = [] for line in code: # Avoid name overloading for each line unambiguous_line = disambiguate_names(line) unambiguous_code.append(unambiguous_line) return unambiguous_code def consider_external_usage(code): # Consider how names will be used outside the code externally_usable_code = [] for line in code: # Consider external usage for each line externally_usable_line = adapt_for_external_usage(line) externally_usable_code.append(externally_usable_line) return externally_usable_code def prefix_helper_names(code): # Prefix helper function and callback names with the calling function's name prefixed_code = [] for line in code: # Prefix helper names for each line prefixed_line = add_helper_prefix(line) prefixed_code.append(prefixed_line) return prefixed_code def order_callbacks(code): # Place callbacks last in the list of parameters callback_ordered_code = [] for line in code: # Order callbacks for each line callback_ordered_line = move_callbacks_last(line) callback_ordered_code.append(callback_ordered_line) return callback_ordered_code def order_for_readability(code): # Order code for readability, with important things near the top and the main function first ordered_code = [] # Order code based on importance and readability ordered_code = reorder_code(code) return ordered_code def add_comments(code, documentation): # Add comments to explain why and how the code was written commented_code = [] for line, doc in zip(code, documentation): # Add comments for each line based on the documentation commented_line = add_comment_to_line(line, doc) commented_code.append(commented_line) return commented_code`
---
def disconnect_concepts(concept1, concept2):

`distinguishing_features = find_distinguishing_features(concept1, concept2)`

`divergent_dimensions = find_divergent_dimensions(concept1, concept2)`

`logical_breaks = break_logical_bridges(concept1, concept2, divergent_dimensions)`

`removed_anchors = remove_anchor_points(concept1, concept2)`

`prompt = craft_disconnecting_prompt(concept1, concept2, logical_breaks, removed_anchors)`

`return evaluate_disconnection_strength(prompt)`
---
def divide_and_conquer(problem):

`if is_base_case(problem):`

`solution = solve_base_case(problem) r`

`return solution else:`

split_logic = determine_split_logic_operation(problem)

`subproblems = split_problem(problem,` split_logic, problem_dependency = ordered_but_independent`)`

`subproblem_solutions = []`

`for subproblem in subproblems:`

`subproblem_solution = divide_and_conquer(subproblem)`

`subproblem_solutions.append(subproblem_solution)`

`solution = combine_solutions(subproblem_solutions)`

`return solution`
---
def harmonize_concepts(concept1, concept2):

`complementary_features = find_complementary_features(concept1, concept2)`

`harmonizing_dimensions = find_harmonizing_dimensions(concept1, concept2)`

`balancing_bridges = create_balancing_bridges(concept1, concept2, harmonizing_dimensions)`

`unifying_anchors = identify_unifying_anchors(concept1, concept2)`

`prompt = craft_harmonizing_prompt(concept1, concept2, balancing_bridges, unifying_anchors)`

`return evaluate_harmony_strength(prompt)`
---
def identify_concepts(text):

`tokenized_text = tokenize(text)`

`named_entities = extract_named_entities(tokenized_text)`

`keywords = extract_keywords(tokenized_text)`

`semantic_network = build_semantic_network(tokenized_text)`

`concept_candidates = generate_concept_candidates(named_entities, keywords, semantic_network)`

`concepts = rank_and_select_concepts(concept_candidates)`

`return concepts`
---
`def manage_technical_debt(project): # Anticipate potential problems potential_problems = anticipate_problems(project) # Identify existing issues existing_issues = identify_issues(project) # Prioritize and discover showstoppers showstoppers = prioritize_and_discover_showstoppers(potential_problems, existing_issues) # Solve showstoppers immediately solved_showstoppers = solve_showstoppers(showstoppers) # Update the project with solved showstoppers updated_project = update_project(project, solved_showstoppers) # Return the updated project return updated_project def anticipate_problems(project): # Analyze the project and identify potential problems potential_problems = [] # Implementation logic to anticipate problems based on project characteristics return potential_problems def identify_issues(project): # Assess the project and identify existing issues existing_issues = [] # Implementation logic to identify issues in the project return existing_issues def prioritize_and_discover_showstoppers(potential_problems, existing_issues): # Combine potential problems and existing issues all_issues = potential_problems + existing_issues # Prioritize issues based on their severity and impact prioritized_issues = prioritize_issues(all_issues) # Identify showstoppers from the prioritized issues showstoppers = identify_showstoppers(prioritized_issues) return showstoppers def solve_showstoppers(showstoppers): # Solve each showstopper immediately solved_showstoppers = [] for showstopper in showstoppers: solution = solve_issue(showstopper) solved_showstoppers.append(solution) return solved_showstoppers def update_project(project, solved_showstoppers): # Update the project by incorporating the solved showstoppers updated_project = apply_solutions(project, solved_showstoppers) return updated_project`
---
`def modify_prompt_for_task(original_prompt, task): core_concepts = extract_core_concepts(original_prompt, task) expanded_concepts = expand_concepts_for_task(core_concepts, task) logical_structure = create_logical_structure(expanded_concepts) modified_prompt = restructure_prompt(original_prompt, logical_structure, expanded_concepts) return evaluate_prompt_effectiveness(modified_prompt, task)`
---
`def power_of_ten_function(input_data, options): # Validate input data and options validate_input(input_data, options) # Process input data using simple, explicit control flow processed_data = process_data(input_data, options) # Apply domain-specific abstractions abstracted_data = apply_abstractions(processed_data) # Enforce limits on loops and queues limited_data = enforce_limits(abstracted_data) # Perform assertions on function arguments, return values, pre/postconditions, and invariants assert_conditions(input_data, options, processed_data, abstracted_data, limited_data) # Return the final result return limited_data def validate_input(input_data, options): # Validate input data and options assert input_data is not None, "Input data cannot be None" assert options is not None, "Options cannot be None" # Additional validation logic def process_data(input_data, options): # Process input data using simple, explicit control flow processed_data = [] for item in input_data: # Apply processing logic based on options processed_item = process_item(item, options) processed_data.append(processed_item) return processed_data def apply_abstractions(processed_data): # Apply domain-specific abstractions abstracted_data = [] for item in processed_data: # Apply abstraction logic abstracted_item = abstract_item(item) abstracted_data.append(abstracted_item) return abstracted_data def enforce_limits(abstracted_data): # Enforce limits on loops and queues limited_data = [] for item in abstracted_data: # Enforce limits on item processing limited_item = limit_item(item) limited_data.append(limited_item) return limited_data def assert_conditions(input_data, options, processed_data, abstracted_data, limited_data): # Perform assertions on function arguments, return values, pre/postconditions, and invariants assert len(input_data) > 0, "Input data cannot be empty" assert len(processed_data) == len(input_data), "Processed data length must match input data length" assert len(abstracted_data) == len(processed_data), "Abstracted data length must match processed data length" assert len(limited_data) == len(abstracted_data), "Limited data length must match abstracted data length" # Additional assertion logic`
---
def refactor_function(function_code):

`function_lines = split_into_lines(function_code)`

`commented_lines = extract_comments(function_lines)`

`code_sections = identify_code_sections(function_lines)`

`basic_functions = []`

`for section in code_sections:`

`basic_function = extract_basic_function(section)`

`basic_functions.append(basic_function)`

`function_purpose = analyze_function_purpose(commented_lines, basic_functions)`

`refactored_function = combine_basic_functions(basic_functions, function_purpose)`

`return refactored_function`
---
`def refine_code_isomorphism(original_code): analyzed_code = analyze_code(original_code) improvement_areas = identify_improvement_areas(analyzed_code) refactored_code = apply_refactoring(original_code, improvement_areas) code_quality = evaluate_code_quality(refactored_code) isomorphism = { 'input': original_code, 'output': refactored_code, 'quality': code_quality } return isomorphism`
---
`def tiger_style_programming(problem, intuition, experience, first_principles, knowledge): # Analyze the problem using reason and first principles problem_analysis = analyze_problem(problem, first_principles) # Apply human intuition and experience to the problem intuitive_insights = apply_intuition(problem, intuition, experience) # Combine problem analysis and intuitive insights solution_design = design_solution(problem_analysis, intuitive_insights, knowledge) # Implement the solution with precision and style implemented_solution = implement_solution(solution_design) # Evaluate the solution based on readability, style, and effectiveness evaluation = evaluate_solution(implemented_solution) return implemented_solution, evaluation def analyze_problem(problem, first_principles): # Break down the problem into its fundamental components problem_components = decompose_problem(problem) # Apply first principles to understand the problem's core problem_core = apply_first_principles(problem_components, first_principles) return problem_core def apply_intuition(problem, intuition, experience): # Use human intuition to identify patterns and insights intuitive_patterns = identify_patterns(problem, intuition) # Draw from experience to generate potential solutions potential_solutions = generate_solutions(problem, experience) return intuitive_patterns, potential_solutions def design_solution(problem_analysis, intuitive_insights, knowledge): # Combine problem analysis and intuitive insights solution_foundation = integrate_analysis_and_intuition(problem_analysis, intuitive_insights) # Apply knowledge to refine and optimize the solution refined_solution = apply_knowledge(solution_foundation, knowledge) return refined_solution def implement_solution(solution_design): # Implement the solution with precision and style implemented_solution = code_with_precision_and_style(solution_design) return implemented_solution def evaluate_solution(implemented_solution): # Evaluate the solution based on readability, style, and effectiveness readability_score = assess_readability(implemented_solution) style_score = assess_style(implemented_solution) effectiveness_score = assess_effectiveness(implemented_solution) return readability_score, style_score, effectiveness_score`
---
struct CodeSection { char* content; char* purpose; char* feedback; }; struct RefactoredCode { char* code; struct CodeSection* sections; int section_count; }; struct RefactoredCode analyze_and_refactor_code(const char* code, const char* R) { // Simulate environment setting set_environment(NO_HALLUCINATE); // Conceptual breakdown struct CodeSection* code_sections = conceptual_breakdown_into_sections(code); int section_count = get_section_count(code_sections); // Analyze and provide feedback for (int i = 0; i < section_count; i++) { code_sections[i].purpose = analyze_section_purpose(code_sections[i].content); code_sections[i].feedback = provide_section_feedback(code_sections[i].content); } // Refactoring steps char* refactored_code = reorganize_code(code_sections, section_count); refactored_code = create_section_functions(refactored_code); refactored_code = add_input_validation(refactored_code); refactored_code = apply_best_practices(refactored_code); // Prepare return structure struct RefactoredCode result; result.code = refactored_code; result.sections = code_sections; result.section_count = section_count; return result; }
---
