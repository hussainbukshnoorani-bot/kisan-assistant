# Feature Specification: To-Do App

**Feature Branch**: `001-todo-app`
**Created**: 2026-09-26
**Status**: Draft
**Input**: User description: "To-do app where users sign up/sign in, create task lists, add tasks with due dates and priorities, and mark them done"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Account Sign-Up and Sign-In (Priority: P1)

A new visitor creates an account with their email address and a password, and is signed in.
A returning user signs in with the same credentials and signs out when finished. Every
user's data is private to them.

**Why this priority**: Every other capability stores personal data; without accounts no list
or task can belong to anyone, so nothing else is usable.

**Independent Test**: Can be fully tested by signing up, signing out, signing back in, and
confirming that protected pages are unreachable while signed out.

**Acceptance Scenarios**:

1. **Given** a visitor with no account, **When** they sign up with a valid email and a
   password meeting the rules, **Then** the account is created and they are signed in.
2. **Given** an email that already has an account, **When** a visitor tries to sign up with it,
   **Then** sign-up is refused with a message that does not reveal whether that email exists
   beyond what is needed to proceed (e.g. "Unable to create account with these details").
3. **Given** a registered user, **When** they sign in with correct credentials, **Then** they
   reach their lists.
4. **Given** a registered user, **When** they sign in with a wrong password, **Then** sign-in is
   refused with a generic "Invalid email or password" message.
5. **Given** a signed-in user, **When** they sign out, **Then** protected pages require signing
   in again.
6. **Given** a visitor who is not signed in, **When** they open any list or task page,
   **Then** they are sent to sign-in.

---

### User Story 2 - Manage Task Lists (Priority: P1)

A signed-in user creates named task lists (e.g. "Work", "Groceries"), sees all their lists,
renames them, and deletes lists they no longer need.

**Why this priority**: Lists are the container for tasks; together with Story 1 and Story 3 they
form the minimum useful product.

**Independent Test**: Can be tested by creating, renaming, and deleting lists and confirming
another user cannot see or change them.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** they create a list named "Work", **Then** "Work" appears
   in their lists.
2. **Given** a user with a list, **When** they rename it, **Then** the new name is shown
   everywhere.
3. **Given** a list containing tasks, **When** the user deletes it and confirms, **Then** the list
   and all its tasks are removed.
4. **Given** a user submits an empty list name, **When** they save, **Then** it is rejected with a
   clear message.
5. **Given** user A's list, **When** user B attempts to view, rename, or delete it, **Then** the
   action is denied and nothing about the list is revealed.

---

### User Story 3 - Add and Complete Tasks (Priority: P1)

Inside a list, the user adds tasks with a title, and optionally a due date and a priority
(Low, Medium, High). They edit tasks, mark them done or not done, and delete them.

**Why this priority**: Capturing and completing tasks is the core purpose of the app.

**Independent Test**: Can be tested by adding tasks with and without due dates and priorities,
toggling completion, editing, and deleting within one list.

**Acceptance Scenarios**:

1. **Given** a list, **When** the user adds a task with only a title, **Then** it appears in the
   list as not done with priority Medium and no due date.
2. **Given** a list, **When** the user adds a task with a title, due date, and priority High,
   **Then** all three values are shown on the task.
3. **Given** an open task, **When** the user marks it done, **Then** it is shown as done; marking
   it again returns it to not done.
4. **Given** a task, **When** the user edits its title, due date, or priority, **Then** the
   changes are saved and shown.
5. **Given** a task, **When** the user deletes it, **Then** it no longer appears.
6. **Given** a task title that is empty or longer than 200 characters, **When** the user saves,
   **Then** it is rejected with a clear message.

---

### User Story 4 - Sort, Filter, and See What's Due (Priority: P2)

Within a list the user sorts tasks by due date or priority and filters to show all, open, or
done tasks. Tasks whose due date has passed and are not done are visibly marked overdue.

**Why this priority**: Makes larger lists manageable and surfaces urgent work, but the app is
usable without it.

**Independent Test**: Can be tested with a list of tasks having mixed due dates, priorities, and
completion states by applying each sort and filter and checking the order and contents.

**Acceptance Scenarios**:

1. **Given** tasks with different due dates, **When** the user sorts by due date, **Then** tasks
   appear earliest first, with tasks without a due date last.
2. **Given** tasks with different priorities, **When** the user sorts by priority, **Then** High
   appears before Medium before Low.
3. **Given** a mix of open and done tasks, **When** the user filters to "Open", **Then** only
   not-done tasks are shown.
4. **Given** an open task whose due date is before today, **When** the list is shown, **Then** the
   task is marked overdue; a done task is never marked overdue.

---

### Edge Cases

- A list with a very large number of tasks (e.g. 1,000+) still loads and is browsable in pages.
- Two lists may share the same name for one user; the app does not block duplicates.
- A due date in the past can be set (e.g. logging a late task) and immediately shows as overdue.
- The user's session expires while editing: the edit is not silently lost; the user is asked to
  sign in again.
- Repeated failed sign-in attempts for one account are rate-limited to slow password guessing.
- The same task is edited in two browser tabs: the last saved change wins.
- A list or task that was deleted in another tab is opened: the user sees a "not found" message.

## Requirements *(mandatory)*

### Functional Requirements

**Accounts**

- **FR-001**: System MUST allow visitors to create an account with an email address and password.
- **FR-002**: System MUST require passwords of at least 8 characters.
- **FR-003**: System MUST reject sign-up for an email that already has an account.
- **FR-004**: Users MUST be able to sign in and sign out.
- **FR-005**: System MUST restrict every list and task to its owner; no user can view or modify
  another user's data.
- **FR-006**: System MUST slow down repeated failed sign-in attempts (at most 5 attempts per
  account per 15 minutes before a temporary block).

**Lists**

- **FR-007**: Users MUST be able to create, view, rename, and delete their task lists.
- **FR-008**: List names MUST be 1–100 characters after trimming whitespace.
- **FR-009**: Deleting a list MUST require confirmation and MUST delete all of its tasks.

**Tasks**

- **FR-010**: Users MUST be able to add a task to a list with a title (1–200 characters),
  an optional due date (calendar date, no time), and a priority of Low, Medium, or High
  (default Medium).
- **FR-011**: Users MUST be able to edit a task's title, due date, and priority.
- **FR-012**: Users MUST be able to mark a task done and mark it not done again.
- **FR-013**: Users MUST be able to delete a task.
- **FR-014**: System MUST show each task's title, due date, priority, and done state.

**Organizing**

- **FR-015**: Users MUST be able to sort a list's tasks by due date (no due date last) or by
  priority (High → Low), and by creation order by default.
- **FR-016**: Users MUST be able to filter a list's tasks to All, Open, or Done.
- **FR-017**: System MUST mark open tasks whose due date is before the user's current date as
  overdue.
- **FR-018**: System MUST present long lists in pages rather than all at once.

**General**

- **FR-019**: All inputs MUST be validated, with clear, specific error messages for each field.
- **FR-020**: The app MUST be fully usable with a keyboard and a screen reader.

### Key Entities

- **User**: A person with an account; identified by email; owns zero or more task lists.
- **Task List**: A named collection of tasks; belongs to exactly one user; has a creation time.
- **Task**: An item in exactly one list; has a title, optional due date, priority
  (Low/Medium/High), done state, and creation and last-updated times.

### Assumptions

- Lists are private to one user; sharing or collaborating on lists is out of scope for this
  feature.
- Sign-in is by email and password only; social sign-in, password reset by email, and email
  verification are out of scope for this feature and may follow as separate features.
- Due dates are dates only (no time of day), evaluated in the user's local date.
- No reminders or notifications, recurring tasks, subtasks, tags, or file attachments.
- Deleted lists and tasks are removed permanently (no trash/undo).
- Web browser only (desktop and mobile widths); no native mobile app.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can sign up and add their first task in under 1 minute.
- **SC-002**: Adding a task takes no more than 3 user actions (e.g. type title, choose priority,
  save).
- **SC-003**: Changes (add, edit, complete, delete) appear on screen in under 1 second for 95% of
  actions.
- **SC-004**: A list of 1,000 tasks opens and becomes usable in under 2.5 seconds.
- **SC-005**: 0 cases in testing where a user can see or change another user's lists or tasks.
- **SC-006**: 90% of first-time users complete "create a list, add a task with a due date, mark it
  done" without help.
- **SC-007**: All primary journeys (sign up, sign in, manage lists, manage tasks) can be completed
  using only a keyboard.
