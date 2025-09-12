### **Testing Checklist: Grouped by Feature/Category**

This checklist categorizes the changes, ensuring a structured testing process for verification in the codebase.

---

### **1. Versioning and Stability**
- [ ] **Version Stability**: Confirm codebase is no longer rebased from Open WebUI at v0.5.7.
- [ ] **Removed Open WebUI Labeling**: Verify that all visible Open WebUI branding has been replaced/removed.
- [ ] **Removed Open WebUI Workflows**: Ensure CI/CD workflows and configurations specific to Open WebUI have been removed.

---

### **2. User Interface Changes**
#### **General UI**
- [x] **Redesigned Prompt Create/Edit Page**: Verify that the UI for creating/editing prompts is functional and matches design specifications.
- [x] **Translation Button Relocation**: Confirm the translation button is accessible from the sidebar menu, and no longer in the settings modal.
- [x] **Help Button Placement**: Confirm the help button is accessible from the top-right menu and operational.
- [ ] **Error Messages UI**: Verify that new error handling descriptions appear correctly in middleware-related interfaces/pages.
- [x] **Improved Prompt View**: Test dark/light mode compatibility and confirm text visibility adjustments.
- [x] **Default Suggestions Spacing**: Confirm AI suggestion text has a space at the start of the sentence.

---

### **3. Multilingual Features**
#### **EN/FR Localization**
- [x] **Documentation Links**: Confirm both English and French documentation links work correctly.
- [x] **Training Courses Links**: Verify the English and French training course links are functional.
- [x] **Model Descriptions**: Confirm that model descriptions render in both official languages.
- [x] **Banner Localization**: Test that localized banners display announcements effectively in multiple languages.
- [ ] **Translation Accuracy**: Verify missing translations have been addressed and improved.

---

### **4. Prompts and Feedback Features**
#### **Prompt/Feedback Enhancements**
- [ ] **Private Prompt Workspace**: Test prompt creation/editing and confirm it is private and secure per user.
- [ ] **Prompt List Pagination**: Verify that pagination and dynamic loading behavior work as expected for long prompt lists.
- [ ] **Prompt Retrieval**: Confirm async behavior on large prompt retrievals and ensure no lockups.
- [ ] **Prompt Visibility**: Confirm both public and private prompts visibility settings work correctly.
- [ ] **Default Prompt Suggestions**: Ensure updated default suggestions are relevant and helpful.
- [ ] **Indexes on Prompt/Feedback**: Verify improvements in database query speeds for prompts/feedback.

#### **Feedback System Changes**
- [ ] **Feedback Management for Admins**: Test admin functionality for exporting or deleting all feedback.
- [ ] **Additional Feedback Columns**: Check analytics display for all added feedback columns.
- [ ] **Feedback Metrics Accuracy**: Verify feedback metrics are correctly calculated in the dashboard.

---

### **5. Metrics Dashboard**
#### **Dashboard Features**
- [ ] **Model Analysis Tabs**: Verify tabs and real-time updates based on model analysis.
- [ ] **Usage Metrics for Admins**: Confirm functional admin dashboard for user tracking.
- [ ] **Metrics Graphs Accuracy**:
  - Historical user enrollment graphs.
  - Inter-prompt latency histogram.
  - Daily tokens and prompt tracking.

#### **Date Range Selection**
- [ ] Test date range selection on metrics graphs for flexible analysis.

#### **Message Metrics Timestamp Standardization**
- [ ] Verify consistency of timestamps in message metrics.

---

### **6. Role and Multitenancy Enhancements**
#### **Roles**
- [ ] **Analysis and Global Analysis Roles**: Confirm new roles allow appropriate metrics dashboard access.
- [x] **Role Updates**: Verify proper functionality when setting a user's role via the Edit User modal.

#### **User Domain**
- [ ] **Domain Check**: Confirm proper multitenancy support via user domain feature.

---

### **7. Performance and Stability**
- [ ] **Database Lock Resolution**: Ensure no open transaction locks the database.
- [ ] **Redis Lock Handling**: Confirm improved error handling and cleanup tasks for Redis locks.

#### **Database Initialization and Indexes**
- [ ] **Initialization Refactor**: Test simplified database initialization for usability and testing.
- [ ] **Indexes**: Verify significant speed improvements in feedback and prompt-related queries.

#### **Improved Health Checks**
- [ ] **Database Health Check**: Confirm that it prevents main thread blockage.

---

### **8. System Security Enhancements**
- [x] **Trivy Security Scan**: Confirm Trivy integration performs vulnerability detection in the CI pipeline.

---

### **9. Additional Features**
#### **MCP Server Integration**
- [ ] Validate functional MCP server connections for enhanced flexibility.

#### **News Desk with MCP**
- [ ] Test centralized update/news management via the News Desk.

#### **Wiki-Grounding**
- [ ] Confirm Wikipedia-grounded information enhances chat responses.

#### **PWA Manifest**
- [x] Ensure the Progressive Web App manifest works across devices.

---

### **10. Fixes**
- **General Bug Fixes**:
  - [x] Ensure pinned chats now offer "unpin" functionality.
  - [x] Test renaming chat items in folders for instant updates.
  - [x] Confirm accurate default model selection for new chats.
  - [ ] Validate corrected issues with date ranges in metrics graphs.
  - [x] Verify JSON exportation has been removed for chats, folders, and archived items.
  - [ ] Confirm proper handling of the tiktoken dependency.
  - [ ] Test malformed Brave search URLs are logged/handled appropriately.

---

### **11. Removed Features**
- [x] **New Version Notification Toast**: Confirm toast notification for version updates is removed.
- [ ] **Actions Specific to Open WebUI**: Verify removed workflows, settings, and references.

---

### **12. Reporting Features**
- **Report Issue Modal**:
  - [x] Confirm issue reporting modal via the exclamation icon works as intended.
- **Suggestion Modal**:
  - [x] Validate the suggestion modal through the lightbulb icon.

---

### **13. Miscellaneous**
- [x] **Alphabetical Models List**: Confirm models are displayed in alphabetical order.
- [ ] **Reindexed Files**: Test reindexing of files in collections where files are available.
- [x] **3 Concurrent Models**: Confirm there’s a limit on selecting only 3 concurrent models.

---

Based on these all changes we've documented in releases:
### Changed

- **⚙️ Versioning Stability**: For stability purposes, we stopped rebasing our code from Open WebUI at v0.5.7.
- **🎨 Redesigned Prompt Create/Edit Page**: A fresh UI to create & edit prompts.
- **🌍 Translation Button**: We've change the location of the language button from the settings modals to the sidebar menu.
- **⚙️ CI/CD Workflows**: Removed broken/unwanted workflows that we're dedicated to Open WebUI.
- **🔗 Open Webui Whitelabeling**: Removed Open WebUI Labeling.
- **🔧 Open Webui Whitelabeling**: Removed Open WebUI.
- **🔗 New Pending Activation Screen**: Pending screen now fits CANChat's Labeling with a link to ask access and in both official languages.
- **⚙️ Help Button Placement**: Moved the help button to the top right menu for easier access and improved user navigation.
- **🔄 Pending Page Enhancements**: The pending page now auto-refreshes upon role changes, providing real-time updates and improved clarity.
- **📊 Metric Dashboard**: The dashboard has now tabs and model analysis providing real-time updates and improved clarity.
- **🛡️ Licensing**: Added Canadian Crown licensing to the project for compliance and transparency.
- **📊 Users Enrollement graph**: Changed graph from daily total users to number of enrollments.
- **💡 Default Suggestions Prompts**: Updated the default suggestions prompts to provide more relevant and helpful suggestions for users.
- **📊 ReadMe Branding Update**: Updated the README file to display CANChat branding.
- **🏆 Model Feedback ELO Hybrid**: Changed the model feedback ELO system to a hybrid solution for improved ranking accuracy.
- **🚨 Improved Error Handling and Reporting**: Improved description and handling of errors in middleware layers.
- **🩺 Improved Database Healthcheck**: Improved database health check to prevent blocking the main thread.
- **🗃️ Refactored Database Initialization**: Refactored database initialization to allow for simpler use and the testing.
- **🤖 User Search**: Allows for more fields to be used when searching in users.
- **🔠 Alphabetical Models List**: Ensured that models are in alphabetical order when displayed.


### Added

- **🔗 Private Prompt Workspace for Users**: Users now have the ability to create/edit their own private prompts on their own Prompt Workspace.
- **💡 Documentation EN/FR**: CANChat's documentation links.
- **🔍 Feedback Survey EN/FR**: Survey enabling user feedback.
- **🌍 Model Descriptions**: Now Models have a quick description in both official languages.
- **📋 Report Issue and Suggestion Forms**: Added forms for reporting issues and submitting suggestions.
- **🌐 User Domain**: Added user domain for multitenancy.
- **📊 Usage Metrics Admin Dashboard**: Added an admin dashboard to track usage metrics.
- **📊 Metrics Dashboard**: The dashboard now includes a graph for historical user enrollment, and date range selection has been added for more flexible analysis.
- **📊 Additional Feedback Columns**: Added more columns to the feedback system for improved analysis and tracking.
- **📈 Analysis and Global Analysis Roles**: Added new roles to access the metrics dashboard, enabling more granular accessibility for analysis.
- **🌍 Banner Localization**: Added support for localized banners, allowing announcements to be displayed in multiple languages.
- **📝 Full Document Retrieval Flag**: Added a flag to enable processing the entire document during web retrieval.
- **🔗 MCP Server Integration**: Integrated support for MCP servers, expanding connection options and deployment flexibility.
- **📰 News Desk with MCP**: Introduced News Desk integration alongside MCP server support, enabling centralized news and update management.
- **🎓 Training Course Links (EN/FR)**: Added links to official training courses in both English and French for easier access to learning resources.
- **🛠️ Issue Reporting Modal**: Access reporting modal via an exclamation icon in chat responses menu.
- **💡 Suggestion Modal**: Access suggestion modal via a lightbulb icon in chat responses menu.
- **🔍 Trivy Security Scan in CI**: Added Trivy scanning to the CI pipeline for automated vulnerability detection and improved security.
- **📑 Prompt List Pagination and Dynamic Loading**: Improved the user experience when viewing prompts by including pagination.
- **✍️ Feedback Management Features for Admins**: Allow for exporting or deleting all Feedback.
- **🗂️ Indexes on Prompt and Feedback**: Added indexes on the `prompt` and `feedback` tables to increase database request speed.
- **🧹 Cleanup scripts for Qdrant**: Added scripts that allow for cleanups of collections.
- **📚 Allowed for re-indexing of files**: Re-index files if a collection is not in place but the file is still available.
- **🌐 Wiki-Grounding**: New functionality which can add information from Wikipedia to chats to enhance a model’s knowledge.
- **📶 Inter-Prompt Latency**: Provide a histogram on inter-prompt latency in metrics.


### Fixed

- **✨ Favicon Logo**: Favicon logos are now using the DSAI logo.
- **🌍 Enhanced Internationalization (i18n)**: Refined and expanded translations.
- **📚 Accessibilty**: Revomed some accessibility issues mainly on the chat/main page.
- **⚙️ Setting Page**: Removed unwanted settings.
- **🔧 Licensing**: Readded required Licensing.
- **🧠 Prompt Suggestions**: When new chat is pressed, prompt suggestions now cycles to all available options.
- **🌍 Tag/Search**: tag:search now translates in both official languages.
- **🔧 Download Chats**: Removed JSON exportation.
- **🌐 Enhanced Internationalization (i18n)**: Refined and expanded translations.
- **📂 Folders**: Removed JSON exportation.
- **✏️ Chat Items**: Renaming chat items when in a chat folder now changes instantly.
- **📂 Archived Chats**: Removed JSON exportation.
- **📌 Pinned Chats**: Pinned chats now see an unpinning option.
- **🖼️ Prompt View**: Fix visual issues and now displays text color correctly based on dark/light mode.
- **🔧 Saving Models Groups RBAC Issue**: Fixed an issue with saving models related to Groups RBAC.
- **🔧 PWA Manifest**: Fixed an issue with the Progressive Web App (PWA) manifest to ensure proper functionality and compatibility across devices.
- **📊 Metric Dashboard**: Fix data issues with daily prompts and tokens
- **📊 Message Metrics Timestamp Standardization**: Message metrics now use a consistent timestamp format improving data accuracy.
- **🌍 Translation Improvements**: Added missing translations to ensure a more consistent and accessible user experience for speakers of all supported languages.
- **💡 AI Suggestion Spacing**: Ensured that AI suggestions always include a space at the start of the sentence for improved readability.
- **📊 Metrics Dashboard**: Resolved issues with date range in graphs for more accurate analysis.
- **📊 Historical Daily User Graph Data Output**: Fixed the historical daily user graph data was incorrect or incomplete, ensuring accurate reporting.
- **🛡️ Brave Search URL Validation**: Now validates the URL of Brave search results and logs out any malformed URLs to improve reliability and security.
- **🔒 Improved Redis Lock Error Handling**: Enhanced error handling for Redis lock management and cleanup tasks, increasing reliability and stability.
- **📝 Improved Accessibility**: Enhanced accessibility for improved user experience.
- **📊 Metrics Dashboard**: Enhanced model metrics access and display for analysts.
- **3️⃣ Limit concurrent model selection**: Limit number of concurrent models to 3.
- **🔍 Full Context Toggles**: Fixed misconfig of full context when using web search.
- **🚨 Typo In Warning**: Fix wording of warning to ensure data veracity in French and English.
- **🗃️ Database Lock**: Fixed issue which caused an open transaction to lock the database.
- **📝 Prompt Visibility**: Fixed public prompts not being visible to users.
- **🚨 Add Missing Dependency**: Add missing tiktoken dependency.
- **💬 Default Model on New Chat**: Fixed the default model not always being used when a new chat is created.
- **🪪 Role Update**: Fixed setting a user's role via the Edit User modal.
- **</> Prompt Retrieval**: Made the calls async to prevent lockup on large requests.

### Removed

- **🔕 New Version Notification Toast Removed**: Removed the toast notification for new version updates.