"""
Predefined Questions Management UI.

Allows HR to view, create, edit, and import predefined question sets.
Uses direct database access instead of REST API calls.
"""

import sys
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

import streamlit as st
from ui.db import get_db_session
from ui.services.predefined_questions_service import PredefinedQuestionsService

# Page configuration
st.set_page_config(
    page_title="Predefined Questions",
    page_icon="",
    layout="wide"
)


def get_roles():
    """Fetch all predefined roles from database"""
    try:
        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.list_roles()
    except Exception as e:
        st.error(f"Error fetching roles: {str(e)}")
        return []


def get_question_sets(role_id=None, is_active=None):
    """Fetch question sets from database"""
    try:
        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.list_question_sets(role_id=role_id, is_active=is_active)
    except Exception as e:
        st.error(f"Error fetching question sets: {str(e)}")
        return []


def get_questions(question_set_id):
    """Fetch questions for a specific question set"""
    try:
        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.list_questions(question_set_id)
    except Exception as e:
        st.error(f"Error fetching questions: {str(e)}")
        return []


def create_role(name, level, description):
    """Create a new role"""
    try:
        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.create_role(name, level, description)
    except Exception as e:
        st.error(f"Error creating role: {str(e)}")
        return None


def create_question_set(role_id, name, version, description, is_active):
    """Create a new question set"""
    try:
        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.create_question_set(
                role_id, name, version, description, is_active
            )
    except Exception as e:
        st.error(f"Error creating question set: {str(e)}")
        return None


def import_from_document(file, role_name, role_level, role_description,
                        question_set_name, question_set_version,
                        question_set_description, is_active):
    """Import questions from document"""
    try:
        file_content = file.getvalue()
        filename = file.name

        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.import_from_document(
                file_content=file_content,
                filename=filename,
                role_name=role_name,
                role_level=role_level,
                role_description=role_description,
                question_set_name=question_set_name,
                question_set_version=question_set_version,
                question_set_description=question_set_description,
                is_active=is_active
            )
    except Exception as e:
        st.error(f"Error importing document: {str(e)}")
        return None


def activate_question_set(question_set_id):
    """Activate a question set"""
    try:
        with get_db_session() as db:
            service = PredefinedQuestionsService(db)
            return service.activate_question_set(question_set_id)
    except Exception as e:
        st.error(f"Error activating question set: {str(e)}")
        return None


def _get_assessment_key(what_assesses):
    """Create a hashable key from what_assesses list for grouping."""
    if not what_assesses:
        return tuple()
    return tuple(sorted(what_assesses))


def _group_questions_by_assessment(questions):
    """
    Group questions that share the same assessment criteria.

    Returns list of groups, where each group is a dict with:
    - questions: list of questions in this group
    - what_assesses: shared assessment criteria
    - expected_answer_pattern: shared expected answer (if same for all)
    """
    from collections import OrderedDict

    groups = OrderedDict()

    for q in questions:
        key = _get_assessment_key(q.get('what_assesses', []))

        if key not in groups:
            groups[key] = {
                'questions': [],
                'what_assesses': q.get('what_assesses', []),
                'expected_answer_pattern': q.get('expected_answer_pattern'),
            }

        groups[key]['questions'].append(q)

        # If expected_answer_pattern differs, mark as None (not shared)
        if groups[key]['expected_answer_pattern'] != q.get('expected_answer_pattern'):
            groups[key]['expected_answer_pattern'] = None

    return list(groups.values())


@st.dialog("Question Set Details", width="large")
def show_question_set_details(question_set, roles):
    """Modal to display question set details"""
    # Find role name
    role = next((r for r in roles if r['id'] == question_set['role_id']), None)
    role_display = f"{role['name']} ({role['level']})" if role else "Unknown"

    # Header
    st.subheader(question_set['name'])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Role", role_display)
    with col2:
        st.metric("Version", question_set['version'])
    with col3:
        status_label = "Active " if question_set['is_active'] else "Inactive "
        st.metric("Status", status_label)

    if question_set.get('description'):
        st.info(f"**Description:** {question_set['description']}")

    # Activate button
    if not question_set['is_active']:
        if st.button("Activate This Question Set", use_container_width=True):
            with st.spinner("Activating..."):
                result = activate_question_set(question_set['id'])
                if result:
                    st.success("Question set activated!")
                    st.rerun()

    st.divider()

    # Fetch and display questions
    questions = get_questions(question_set['id'])

    if questions:
        st.markdown(f"### Questions ({len(questions)})")

        # Group questions by category
        from collections import defaultdict
        questions_by_category = defaultdict(list)
        for q in sorted(questions, key=lambda x: x['order']):
            questions_by_category[q['category']].append(q)

        # Display each category with its questions grouped by assessment
        for category, category_questions in questions_by_category.items():
            st.markdown(f"#### {category}")
            st.caption(f"{len(category_questions)} question(s)")

            # Group questions within category by shared assessment criteria
            assessment_groups = _group_questions_by_assessment(category_questions)

            for group in assessment_groups:
                group_questions = group['questions']
                what_assesses = group['what_assesses']
                shared_expected_answer = group['expected_answer_pattern']

                # If multiple questions share the same assessment, display them together
                if len(group_questions) > 1:
                    # Create expander title showing question count
                    first_q = group_questions[0]
                    expander_title = f"{len(group_questions)} questions - {first_q['question_text'][:50]}..."

                    with st.expander(expander_title):
                        # Show all questions in the group
                        st.markdown("**Questions:**")
                        for idx, q in enumerate(group_questions, 1):
                            st.markdown(f"{idx}. {q['question_text']}")

                        # Show shared assessment criteria once
                        if what_assesses:
                            st.markdown("**What this assesses:**")
                            for assess in what_assesses:
                                st.markdown(f"* {assess}")

                        # Show shared expected answer pattern if all questions share it
                        if shared_expected_answer:
                            st.markdown("**Expected answer pattern:**")
                            st.markdown(f"_{shared_expected_answer}_")
                        else:
                            # Show individual expected answers if they differ
                            has_individual_patterns = any(q.get('expected_answer_pattern') for q in group_questions)
                            if has_individual_patterns:
                                st.markdown("**Expected answer patterns:**")
                                for idx, q in enumerate(group_questions, 1):
                                    if q.get('expected_answer_pattern'):
                                        st.markdown(f"_{idx}. {q['expected_answer_pattern']}_")
                else:
                    # Single question - display as before
                    q = group_questions[0]

                    with st.expander(f"{q['question_text'][:60]}..."):
                        st.markdown(f"**Question:**")
                        st.markdown(f"> {q['question_text']}")

                        if what_assesses:
                            st.markdown("**What this assesses:**")
                            for assess in what_assesses:
                                st.markdown(f"* {assess}")

                        if q.get('expected_answer_pattern'):
                            st.markdown("**Expected answer pattern:**")
                            st.markdown(f"_{q['expected_answer_pattern']}_")

            st.markdown("---")  # Separator between categories
    else:
        st.warning("No questions found in this set.")

    # Close button
    if st.button("Close", use_container_width=True, type="primary"):
        st.rerun()


def main():
    """Main UI for predefined questions management"""

    st.title("Predefined Questions Management")

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["View Questions", "Create", "Import from Document"])

    # ============ TAB 1: VIEW QUESTIONS ============
    with tab1:
        st.header("Question Sets")

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            roles = get_roles()
            role_options = {f"{r['name']} ({r['level']})": r['id'] for r in roles}
            role_options = {"All Roles": None, **role_options}
            selected_role_display = st.selectbox("Filter by Role", list(role_options.keys()))
            selected_role_id = role_options[selected_role_display]

        with col2:
            active_filter = st.selectbox("Filter by Status", ["All", "Active Only", "Inactive Only"])
            is_active_filter = None if active_filter == "All" else (active_filter == "Active Only")

        # Fetch question sets
        question_sets = get_question_sets(role_id=selected_role_id, is_active=is_active_filter)

        if question_sets:
            st.markdown(f"**Found {len(question_sets)} question set(s)**")
            st.markdown("---")

            # Display as grid of cards (3 per row)
            for idx in range(0, len(question_sets), 3):
                cols = st.columns(3)

                for col_idx, qs in enumerate(question_sets[idx:idx+3]):
                    # Find role name
                    role = next((r for r in roles if r['id'] == qs['role_id']), None)
                    role_display = f"{role['name']} ({role['level']})" if role else "Unknown"

                    with cols[col_idx]:
                        # Create compact card with container
                        with st.container(border=True):
                            # Status and title in same line
                            status_icon = "[Active]" if qs['is_active'] else "[Inactive]"
                            st.markdown(f"{status_icon} **{qs['name']}**")

                            # Role, version in compact format
                            st.caption(f"{role_display} - {qs['version']}")
                            st.caption(f"Created: {qs['created_at'][:10]}")

                            # View details button (compact)
                            if st.button("View", key=f"view_{qs['id']}", use_container_width=True):
                                show_question_set_details(qs, roles)

        else:
            st.info("No question sets found. Create one or import from a document.")

    # ============ TAB 2: CREATE ============
    with tab2:
        st.header("Create New Question Set")

        # Role selection OUTSIDE form (so it's interactive)
        st.subheader("1. Select or Create Role")

        roles = get_roles()

        # If no roles exist, must create one
        if len(roles) == 0:
            st.info("No roles available. Please create a new role first.")
            create_new_role = True
        else:
            # Allow choosing between existing role or creating new one
            create_new_role = st.checkbox("Create new role (uncheck to use existing)", value=False)

        if create_new_role:
            col1, col2 = st.columns(2)
            with col1:
                new_role_name = st.text_input(
                    "Role Name",
                    placeholder="e.g., Fullstack Developer",
                    key="create_role_name",
                )
            with col2:
                new_role_level = st.selectbox("Seniority Level", ["Junior", "Mid", "Senior", "Lead", "Principal"])

            new_role_description = st.text_area(
                "Role Description (optional)",
                key="create_role_description",
            )
            role_to_use = None
        else:
            if roles:
                role_options = {f"{r['name']} ({r['level']})": r['id'] for r in roles}
                selected_role_display = st.selectbox("Select Role", list(role_options.keys()), key="create_select_role")
                role_to_use = role_options[selected_role_display]

                # Show selected role info
                selected_role_info = next((r for r in roles if r['id'] == role_to_use), None)
                if selected_role_info:
                    st.success(f"Using: {selected_role_info['name']} ({selected_role_info['level']})")
            else:
                st.warning("No roles available. Please create a new role.")
                role_to_use = None

        st.markdown("---")

        # Form starts here
        with st.form("create_question_set_form"):
            st.subheader("2. Question Set Details")

            col1, col2 = st.columns(2)
            with col1:
                qs_name = st.text_input(
                    "Question Set Name",
                    placeholder="e.g., Fullstack Senior - 2026 Q1",
                    key="create_qs_name",
                )
            with col2:
                qs_version = st.text_input(
                    "Version",
                    placeholder="e.g., v1.0",
                    key="create_qs_version",
                )

            qs_description = st.text_area("Description (optional)")
            qs_is_active = st.checkbox("Set as active", value=False)

            st.info("After creating the question set, you can add questions manually via the API or import from a document.")

            submitted = st.form_submit_button("Create Question Set", type="primary")

            if submitted:
                if create_new_role:
                    if not new_role_name or not new_role_level:
                        st.error("Please fill in all role fields.")
                    else:
                        with st.spinner("Creating role..."):
                            new_role = create_role(new_role_name, new_role_level, new_role_description)
                            if new_role:
                                role_to_use = new_role['id']
                                st.success(f"Role created: {new_role_name}")

                if role_to_use and qs_name and qs_version:
                    with st.spinner("Creating question set..."):
                        result = create_question_set(
                            role_to_use, qs_name, qs_version, qs_description, qs_is_active
                        )
                        if result:
                            st.success("Question set created successfully!")
                            st.balloons()
                            st.rerun()
                else:
                    st.error("Please fill in all required fields.")

    # ============ TAB 3: IMPORT FROM DOCUMENT ============
    with tab3:
        st.header("Import Questions from Document")

        st.markdown("""
        Upload a document (.md, .docx, .txt, .pdf) containing interview questions.
        The AI will automatically parse and structure the questions.
        """)

        # Role selection OUTSIDE form (so it's interactive)
        st.subheader("Role Information")

        # Get existing roles
        import_roles = get_roles()

        if import_roles:
            use_existing_role = st.checkbox("Use existing role (uncheck to create new)", value=True)
        else:
            use_existing_role = False
            st.info("No existing roles. Please create a new role below.")

        if use_existing_role and import_roles:
            # Select from existing roles
            role_options = {f"{r['name']} ({r['level']})": r for r in import_roles}
            selected_role_display = st.selectbox("Select Role", list(role_options.keys()), key="import_select_role")
            selected_import_role = role_options[selected_role_display]

            import_role_name = selected_import_role['name']
            import_role_level = selected_import_role['level']
            import_role_description = selected_import_role.get('description')

            st.success(f"Using: {import_role_name} ({import_role_level})")
        else:
            # Create new role
            col1, col2 = st.columns(2)
            with col1:
                import_role_name = st.text_input(
                    "Role Name",
                    placeholder="e.g., Fullstack Developer",
                    key="import_role_name_input",
                )
            with col2:
                import_role_level = st.selectbox("Level", ["Junior", "Mid", "Senior", "Lead", "Principal"])

            import_role_description = st.text_area(
                "Role Description (optional)",
                key="import_role_description",
            )

        st.markdown("---")

        # Form starts here (with file upload and question set info)
        with st.form("import_document_form"):
            uploaded_file = st.file_uploader(
                "Choose a document file",
                type=['md', 'docx', 'txt', 'pdf'],
                help="Upload a document containing structured interview questions"
            )

            st.subheader("Question Set Information")
            col1, col2 = st.columns(2)
            with col1:
                import_qs_name = st.text_input(
                    "Question Set Name",
                    placeholder="e.g., Fullstack Senior - 2026 Q1",
                    key="import_qs_name",
                )
            with col2:
                import_qs_version = st.text_input(
                    "Version",
                    placeholder="e.g., v1.0",
                    key="import_qs_version",
                )

            import_qs_description = st.text_area("Question Set Description (optional)")
            import_is_active = st.checkbox("Set as active", value=True, key="import_active")

            submitted = st.form_submit_button("Import Document", type="primary")

            if submitted:
                if not uploaded_file:
                    st.error("Please upload a document file.")
                elif not import_role_name or not import_role_level:
                    st.error("Please fill in role information.")
                elif not import_qs_name or not import_qs_version:
                    st.error("Please fill in question set information.")
                else:
                    with st.spinner("Parsing document with AI... This may take a moment."):
                        result = import_from_document(
                            uploaded_file,
                            import_role_name,
                            import_role_level,
                            import_role_description,
                            import_qs_name,
                            import_qs_version,
                            import_qs_description,
                            import_is_active
                        )

                        if result:
                            st.success("Document imported successfully!")
                            st.balloons()

                            # Show summary
                            st.subheader("Import Summary")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Question Set", result['name'])
                                st.metric("Version", result['version'])
                            with col2:
                                st.metric("Questions Imported", len(result.get('questions', [])))
                                st.metric("Status", "Active" if result['is_active'] else "Inactive")

                            st.info("You can now view the imported questions in the 'View Questions' tab.")


if __name__ == "__main__":
    main()
