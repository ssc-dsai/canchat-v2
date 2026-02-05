// Helper function to extract tool name from MCP display name
const extractToolName = (displayName: string): string => {
	// If it starts with "MCP: ", remove that prefix
	if (displayName.startsWith('MCP: ')) {
		return displayName.substring(5);
	}
	return displayName;
};

// Helper function to get localized MCP tool descriptions
const getMCPToolDescription = (toolName: string, i18n: any): string => {
	// Extract the actual function name
	const actualToolName = extractToolName(toolName);

	// Map tool names to English descriptions (which serve as translation keys)
	const toolDescriptions: Record<string, string> = {
		get_current_time: 'Get current date and time in any timezone',
		get_top_headlines: 'Get latest news headlines from around the world',
		mpo_search_documents_fast: 'Fast search MPO SharePoint documents (sub-1 second)',
		mpo_list_folder_contents: 'List files in MPO SharePoint folders',
		mpo_get_document_by_id: 'Retrieve MPO SharePoint document by ID from search results',
		mpo_analyze_all_documents_for_content: 'Search and retrieve MPO SharePoint documents',
		mpo_get_sharepoint_document_content: 'Search and retrieve MPO SharePoint documents',
		mpo_get_all_documents_comprehensive: 'Search and retrieve MPO SharePoint documents',
		mpo_check_sharepoint_permissions: 'Search and retrieve MPO SharePoint documents',
		pmo_search_documents_fast: 'Fast search PMO SharePoint documents (sub-1 second)',
		pmo_list_folder_contents: 'List files in PMO SharePoint folders',
		pmo_get_document_by_id: 'Retrieve PMO SharePoint document by ID from search results',
		pmo_analyze_all_documents_for_content: 'Search and retrieve PMO SharePoint documents',
		pmo_get_sharepoint_document_content: 'Search and retrieve PMO SharePoint documents',
		pmo_get_all_documents_comprehensive: 'Search and retrieve PMO SharePoint documents',
		pmo_check_sharepoint_permissions: 'Search and retrieve PMO SharePoint documents'
	};

	const englishDescription = toolDescriptions[actualToolName];
	if (englishDescription) {
		const translated = i18n.t(englishDescription);
		return translated;
	}

	// Fallback to formatted tool name (short and clean)
	const fallback = actualToolName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	return fallback;
};

// Helper function to get localized MCP tool name
export const getMCPToolName = (toolName: string, i18n: any): string => {
	// Extract the actual function name
	const actualToolName = extractToolName(toolName);

	// Map tool names to English display names (which serve as translation keys)
	const toolNames: Record<string, string> = {
		get_current_time: 'MCP: Current Time',
		get_top_headlines: 'MCP: News Headlines',
		mpo_search_documents_fast: 'MCP: MPO SharePoint',
		mpo_list_folder_contents: 'MCP: MPO SharePoint',
		mpo_get_document_by_id: 'MCP: MPO SharePoint (By ID)',
		mpo_analyze_all_documents_for_content: 'MCP: MPO SharePoint',
		mpo_get_sharepoint_document_content: 'MCP: MPO SharePoint',
		mpo_get_all_documents_comprehensive: 'MCP: MPO SharePoint',
		mpo_check_sharepoint_permissions: 'MCP: MPO SharePoint',
		pmo_search_documents_fast: 'MCP: PMO SharePoint',
		pmo_list_folder_contents: 'MCP: PMO SharePoint',
		pmo_get_document_by_id: 'MCP: PMO SharePoint (By ID)',
		pmo_analyze_all_documents_for_content: 'MCP: PMO SharePoint',
		pmo_get_sharepoint_document_content: 'MCP: PMO SharePoint',
		pmo_get_all_documents_comprehensive: 'MCP: PMO SharePoint',
		pmo_check_sharepoint_permissions: 'MCP: PMO SharePoint'
	};

	const englishName = toolNames[actualToolName];
	if (englishName) {
		const translated = i18n.t(englishName);
		return translated;
	}

	// Fallback to formatted tool name with MCP prefix
	const fallback =
		'MCP: ' + actualToolName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	return fallback;
};

// Helper function to get display name for any tool
export const getToolDisplayName = (tool: any, i18n: any): string => {
	if (tool?.meta?.manifest?.is_mcp_tool) {
		// Use originalName (the actual function name) for translation lookup
		const toolNameForTranslation = tool.meta?.manifest?.original_name || tool.name;
		return getMCPToolName(toolNameForTranslation, i18n);
	}
	return tool.name;
};

// Helper function to get tooltip content for tools
export const getToolTooltipContent = (tool: any, i18n: any): string => {
	// Check both isMcp property and meta.manifest.is_mcp_tool
	const isMcpTool = tool?.isMcp || tool?.meta?.manifest?.is_mcp_tool || false;

	if (isMcpTool) {
		// Use originalName (the actual function name) for translation lookup
		const toolNameForTranslation = tool.meta?.manifest?.original_name || tool.name;
		const localizedDescription = getMCPToolDescription(toolNameForTranslation, i18n);
		return localizedDescription;
	}

	// For non-MCP tools, check if description is JSON
	const description = tool.originalDescription || tool.meta?.description || '';
	if (description && description.trim().startsWith('{')) {
		try {
			const parsed = JSON.parse(description);
			// Return the description field from parsed JSON if it exists
			return parsed.description || '';
		} catch (e) {
			// If parsing fails, return as-is
			return description;
		}
	}
	return description;
};
