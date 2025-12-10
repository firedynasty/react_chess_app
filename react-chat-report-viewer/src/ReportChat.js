import React, { useState, useRef, useEffect } from 'react';
import { marked } from 'marked';

// Maximum characters allowed for a file to be sent to Claude
const MAX_CHARS_FOR_CHAT = 100000;

const ReportChat = () => {
  // API and model state
  const [aiProvider, setAiProvider] = useState('ChatGPT'); // 'Anthropic' or 'ChatGPT'
  const [apiKey, setApiKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [webSearchEnabled, setWebSearchEnabled] = useState(false); // Web search for ChatGPT
  const [useSharedKey, setUseSharedKey] = useState(false); // Use Stanley's key via backend
  const [accessCode, setAccessCode] = useState(''); // Access code for shared key
  const [selectedRole, setSelectedRole] = useState('default');

  // View mode state: 'chat' or 'viewer'
  const [viewMode, setViewMode] = useState('chat');
  const [selectedReportKey, setSelectedReportKey] = useState(null);
  const [fontSize, setFontSize] = useState(16);
  const [darkMode, setDarkMode] = useState(true); // Default to dark mode to match sidebar

  // Available roles
  const roles = {
    'default': { name: 'Default (No Role)', prompt: null },
    'socratic_coach': {
      name: 'Socratic Coach',
      prompt: `You are a thoughtful coach using the Socratic method. Your role is to guide learners to discover insights rather than lecturing them.

CORE COACHING PRINCIPLES:

1. ASK, DON'T TELL
   Instead of giving direct answers, ask questions that lead to discovery.
   The learner remembers insights they discover far better than facts they're told.

2. VALIDATE FIRST, THEN PROBE
   Always find something reasonable in the learner's thinking before challenging it.
   This keeps them open and engaged rather than defensive.
   Example: "I see you were trying to [X] - that's good thinking! But let me ask..."

3. GUIDE TO PRINCIPLES, NOT JUST ANSWERS
   Connect specific situations to broader understanding.
   This builds transferable knowledge they can apply to new situations.

4. ONE QUESTION AT A TIME
   Don't overwhelm with multiple questions. Ask one, wait for reflection,
   then build on their response.

5. END WITH ACTION
   Give one concrete thing to study or practice. Not a list of five things.

COACHING CONVERSATION FLOW:

Step 1: UNDERSTAND THEIR THINKING
- "What were you trying to accomplish?"
- "What was your reasoning?"
- "What options did you consider?"

Step 2: REVEAL THE GAP
Help them see what they missed through questions, not statements.
- "What happens if...?"
- "How does this compare to...?"
- "What principle might apply here?"

Step 3: TEACH THE PRINCIPLE
Connect to a broader concept they can remember and reuse.

Step 4: GIVE CONCRETE PRACTICE
One specific exercise or study task.

TONE: Encouraging, curious, thought-provoking. Like a wise mentor, not a critic.

IMPORTANT:
- Keep responses focused and under 200 words when possible
- End with a thought-provoking question OR a concrete study suggestion
- Never be condescending - treat learners as capable people who just need guidance
- If they're stuck, give a small hint, then ask a follow-up question`
    },
  };

  // Reports state
  const [loadedReports, setLoadedReports] = useState({}); // {filename: content}
  const [isReportsModalOpen, setIsReportsModalOpen] = useState(false);

  // Preloaded folders state
  const [preloadedFolders, setPreloadedFolders] = useState([]); // [{name, fileCount}]
  const [selectedPreloadedFolder, setSelectedPreloadedFolder] = useState('');
  const [isLoadingPreloaded, setIsLoadingPreloaded] = useState(false);

  // Literature state - only one file can be literature at a time
  const [literatureFile, setLiteratureFile] = useState(null); // filename of literature file
  const [literatureSearchTerm, setLiteratureSearchTerm] = useState('');
  const [literatureNumLines, setLiteratureNumLines] = useState(500);
  const [literatureFoundLine, setLiteratureFoundLine] = useState(null);
  const [literatureDisplayContent, setLiteratureDisplayContent] = useState(null);

  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Refs
  const chatContainerRef = useRef(null);
  const fileInputRef = useRef(null);
  const literatureContentRef = useRef(null);

  // Available models
  const anthropicModels = {
    'Claude 3.5 Haiku': 'claude-3-5-haiku-20241022',
    'Claude 3.5 Sonnet': 'claude-3-5-sonnet-20241022',
    'Claude Sonnet 4': 'claude-sonnet-4-20250514',
    'Claude Opus 4.5': 'claude-opus-4-5-20251101',
  };

  const openaiModels = {
    'GPT-4o': 'gpt-4o',
    'GPT-4o Mini': 'gpt-4o-mini',
    'GPT-4 Turbo': 'gpt-4-turbo',
    'GPT-3.5 Turbo': 'gpt-3.5-turbo',
    'o1': 'o1',
    'o1 Mini': 'o1-mini',
  };

  // Get current models based on provider
  const models = aiProvider === 'ChatGPT' ? openaiModels : anthropicModels;

  // Reset model when provider changes
  useEffect(() => {
    if (aiProvider === 'ChatGPT') {
      setSelectedModel('gpt-4o-mini');
    } else {
      setSelectedModel('claude-3-5-haiku-20241022');
    }
  }, [aiProvider]);

  // Fetch preloaded folders on mount
  useEffect(() => {
    const fetchPreloadedFolders = async () => {
      try {
        const response = await fetch('/preloaded/index.json');
        if (response.ok) {
          const data = await response.json();
          setPreloadedFolders(data.folders || []);
        }
      } catch (err) {
        console.log('No preloaded folders available:', err);
      }
    };
    fetchPreloadedFolders();
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle preloaded folder selection
  const handlePreloadedFolderSelect = async (folderName) => {
    if (!folderName) return;

    setIsLoadingPreloaded(true);
    setSelectedPreloadedFolder(folderName);

    try {
      const response = await fetch(`/preloaded/${folderName}.json`);
      if (!response.ok) {
        throw new Error(`Failed to load folder: ${folderName}`);
      }

      const filesData = await response.json();

      // Convert to the loadedReports format
      const newReports = {};
      for (const [filename, content] of Object.entries(filesData)) {
        newReports[filename] = content;
      }

      setLoadedReports(newReports);

      // Auto-select first report
      const filenames = Object.keys(newReports);
      if (filenames.length > 0) {
        setSelectedReportKey(filenames[0]);
      }

      // Auto-set largest file over MAX_CHARS as literature
      const largeFiles = Object.entries(newReports)
        .filter(([_, content]) => content.length > MAX_CHARS_FOR_CHAT)
        .sort((a, b) => b[1].length - a[1].length);

      if (largeFiles.length > 0) {
        setLiteratureFile(largeFiles[0][0]);
      } else {
        setLiteratureFile(null);
      }

      setLiteratureDisplayContent(null);
      setLiteratureFoundLine(null);

      setIsReportsModalOpen(true);
    } catch (err) {
      console.error('Error loading preloaded folder:', err);
      alert(`Error loading folder: ${err.message}`);
    } finally {
      setIsLoadingPreloaded(false);
    }
  };

  // Handle folder selection
  const handleFolderSelect = async (event) => {
    const files = Array.from(event.target.files);
    const textFiles = files.filter(file => {
      const name = file.name.toLowerCase();
      return name.endsWith('.txt') || name.endsWith('.md');
    });

    if (textFiles.length === 0) {
      alert('No .txt or .md files found in selected folder');
      return;
    }

    // Sort files naturally
    textFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));

    // Read all files
    const newReports = {};
    for (const file of textFiles) {
      try {
        const content = await file.text();
        newReports[file.name] = content;
      } catch (err) {
        console.error(`Error reading ${file.name}:`, err);
      }
    }

    setLoadedReports(prev => ({ ...prev, ...newReports }));
    // Auto-select first report if none selected
    if (!selectedReportKey && Object.keys(newReports).length > 0) {
      setSelectedReportKey(Object.keys(newReports)[0]);
    }

    // Auto-set largest file over MAX_CHARS as literature
    const largeFiles = Object.entries(newReports)
      .filter(([_, content]) => content.length > MAX_CHARS_FOR_CHAT)
      .sort((a, b) => b[1].length - a[1].length); // Sort by size descending

    if (largeFiles.length > 0 && !literatureFile) {
      // Set the largest file as literature
      setLiteratureFile(largeFiles[0][0]);
    }

    setIsReportsModalOpen(true);
  };

  // Change font size
  const changeFontSize = (delta) => {
    setFontSize(prev => Math.max(10, Math.min(32, prev + delta)));
  };

  // Check if file is markdown
  const isMarkdown = (filename) => {
    return filename?.toLowerCase().endsWith('.md');
  };

  // Render markdown content
  const renderMarkdown = (content) => {
    if (!content) return '';
    return marked.parse(content);
  };

  // Remove a report
  const removeReport = (filename) => {
    // If removing the literature file, clear literature state
    if (filename === literatureFile) {
      setLiteratureFile(null);
      setLiteratureDisplayContent(null);
      setLiteratureFoundLine(null);
    }
    setLoadedReports(prev => {
      const newReports = { ...prev };
      delete newReports[filename];
      return newReports;
    });
  };

  // Toggle literature status for a file
  const toggleLiterature = (filename) => {
    if (literatureFile === filename) {
      // Unset literature
      setLiteratureFile(null);
      setLiteratureDisplayContent(null);
      setLiteratureFoundLine(null);
    } else {
      // Set as literature
      setLiteratureFile(filename);
      setLiteratureDisplayContent(null);
      setLiteratureFoundLine(null);
      setLiteratureSearchTerm('');
    }
  };

  // Search and extract from literature file
  const searchLiterature = (startFromLine = 0) => {
    if (!literatureFile || !loadedReports[literatureFile]) {
      alert('No literature file selected');
      return -1;
    }
    if (!literatureSearchTerm.trim()) {
      alert('Please enter a search term');
      return -1;
    }

    const content = loadedReports[literatureFile];
    const lines = content.split('\n');
    const searchLower = literatureSearchTerm.toLowerCase().trim();

    // Find the line containing the search term starting from startFromLine
    let foundLineIndex = -1;
    for (let i = startFromLine; i < lines.length; i++) {
      if (lines[i].toLowerCase().includes(searchLower)) {
        foundLineIndex = i;
        break;
      }
    }

    if (foundLineIndex === -1) {
      if (startFromLine === 0) {
        alert(`"${literatureSearchTerm}" not found in the text`);
      } else {
        alert(`No more occurrences found. Reached end of text.`);
      }
      return -1;
    }

    // Extract lines from found position
    const numLines = Math.max(1, Math.min(5000, literatureNumLines));
    const extractedLines = lines.slice(foundLineIndex, foundLineIndex + numLines);

    setLiteratureFoundLine(foundLineIndex + 1); // 1-indexed for display
    setLiteratureDisplayContent(extractedLines.join('\n'));

    // Scroll to top of literature content
    setTimeout(() => {
      if (literatureContentRef.current) {
        literatureContentRef.current.scrollTop = 0;
      }
    }, 0);

    return foundLineIndex;
  };

  // Find next occurrence
  const findNextLiterature = () => {
    if (!literatureFoundLine) {
      searchLiterature(0);
      return;
    }
    // Start searching from the line after current found line
    searchLiterature(literatureFoundLine); // literatureFoundLine is 1-indexed, so this is correct
  };

  // Find previous occurrence
  const findPrevLiterature = () => {
    if (!literatureFile || !loadedReports[literatureFile]) {
      alert('No literature file selected');
      return;
    }
    if (!literatureSearchTerm.trim()) {
      alert('Please enter a search term');
      return;
    }

    const content = loadedReports[literatureFile];
    const lines = content.split('\n');
    const searchLower = literatureSearchTerm.toLowerCase().trim();

    // Start searching backwards from the line before current found line
    const startLine = literatureFoundLine ? literatureFoundLine - 2 : lines.length - 1; // -2 because foundLine is 1-indexed

    let foundLineIndex = -1;
    for (let i = startLine; i >= 0; i--) {
      if (lines[i].toLowerCase().includes(searchLower)) {
        foundLineIndex = i;
        break;
      }
    }

    if (foundLineIndex === -1) {
      alert(`No previous occurrences found. Reached beginning of text.`);
      return;
    }

    // Extract lines from found position
    const numLines = Math.max(1, Math.min(5000, literatureNumLines));
    const extractedLines = lines.slice(foundLineIndex, foundLineIndex + numLines);

    setLiteratureFoundLine(foundLineIndex + 1); // 1-indexed for display
    setLiteratureDisplayContent(extractedLines.join('\n'));

    // Scroll to top of literature content
    setTimeout(() => {
      if (literatureContentRef.current) {
        literatureContentRef.current.scrollTop = 0;
      }
    }, 0);
  };

  // Display next set of lines (continue reading)
  const nextLinesLiterature = () => {
    if (!literatureFile || !loadedReports[literatureFile]) {
      alert('No literature file selected');
      return;
    }
    if (!literatureFoundLine) {
      alert('Please search for something first');
      return;
    }

    const content = loadedReports[literatureFile];
    const lines = content.split('\n');
    const numLines = Math.max(1, Math.min(5000, literatureNumLines));

    // Start from end of current display
    const newStartLine = literatureFoundLine - 1 + numLines; // -1 because foundLine is 1-indexed

    if (newStartLine >= lines.length) {
      alert('Reached end of text.');
      return;
    }

    const extractedLines = lines.slice(newStartLine, newStartLine + numLines);

    setLiteratureFoundLine(newStartLine + 1); // 1-indexed for display
    setLiteratureDisplayContent(extractedLines.join('\n'));

    // Scroll to top of literature content
    setTimeout(() => {
      if (literatureContentRef.current) {
        literatureContentRef.current.scrollTop = 0;
      }
    }, 0);
  };

  // Copy selected text to clipboard
  const copySelection = async () => {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (!selectedText) {
      alert('No text highlighted. Please highlight/select text first.');
      return;
    }

    try {
      await navigator.clipboard.writeText(selectedText);
      alert('Copied to clipboard!');
    } catch (err) {
      console.error('Clipboard write failed:', err);
      alert('Failed to copy to clipboard');
    }
  };

  // Clear all reports
  const clearAllReports = () => {
    setLoadedReports({});
    setLiteratureFile(null);
    setLiteratureDisplayContent(null);
    setLiteratureFoundLine(null);
    setIsReportsModalOpen(false);
  };

  // Get reports that can be sent to chat (excludes literature and files too large)
  const getReportsForChat = () => {
    return Object.entries(loadedReports).filter(
      ([filename, content]) => filename !== literatureFile && content.length <= MAX_CHARS_FOR_CHAT
    );
  };

  // Get count of excluded files (too large)
  const getExcludedFilesCount = () => {
    return Object.entries(loadedReports).filter(
      ([filename, content]) => filename === literatureFile || content.length > MAX_CHARS_FOR_CHAT
    ).length;
  };

  // Build system prompt with role and reports context
  const buildSystemPrompt = () => {
    const parts = [];

    // Add role prompt if not default
    const rolePrompt = roles[selectedRole]?.prompt;
    if (rolePrompt) {
      parts.push(rolePrompt);
    }

    // Add reports context if files are loaded (excluding literature file AND files over MAX_CHARS)
    const reportEntries = getReportsForChat();
    const excludedFiles = Object.entries(loadedReports).filter(
      ([filename, content]) => filename === literatureFile || content.length > MAX_CHARS_FOR_CHAT
    );

    if (reportEntries.length > 0) {
      let reportsContext = `You have access to the following report files. Use them to answer questions and provide analysis.

Here are the loaded reports:

`;
      for (const [filename, content] of reportEntries) {
        reportsContext += `--- FILE: ${filename} ---
${content}

`;
      }

      // Mention excluded files
      if (excludedFiles.length > 0) {
        const excludedNames = excludedFiles.map(([name]) => name).join(', ');
        reportsContext += `Note: The following file(s) are loaded but not included in context due to size: ${excludedNames}. You can help the user find specific sections or chapters to read in them.\n`;
      }

      parts.push(reportsContext);
    } else if (excludedFiles.length > 0) {
      // Only large/literature files loaded, no small reports
      const excludedNames = excludedFiles.map(([name]) => name).join(', ');
      parts.push(`Note: The user has file(s) loaded for reading: ${excludedNames}. These are not included in context due to size, but you can help the user find specific sections or chapters to read based on your knowledge.\n`);
    }

    return parts.length > 0 ? parts.join('\n\n') : null;
  };

  // Send message to API
  const sendMessage = async () => {
    const needsApiKey = !(aiProvider === 'ChatGPT' && useSharedKey);
    if (!inputValue.trim()) return;
    if (needsApiKey && !apiKey) {
      alert(`Please enter your ${aiProvider === 'ChatGPT' ? 'OpenAI' : 'Anthropic'} API key`);
      return;
    }

    const userMessage = { role: 'user', content: inputValue };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setIsLoading(true);

    try {
      const systemPrompt = buildSystemPrompt();
      let assistantMessage;

      if (aiProvider === 'ChatGPT') {
        // OpenAI API call
        const openaiMessages = [];
        if (systemPrompt) {
          openaiMessages.push({ role: 'system', content: systemPrompt });
        }
        openaiMessages.push(...newMessages.map(m => ({ role: m.role, content: m.content })));

        // Check if running locally (localhost) or on Vercel
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

        if (isLocalhost && !useSharedKey) {
          // Local development: call OpenAI directly (for testing with your own key)
          let response;

          if (webSearchEnabled) {
            // Use Responses API with web_search tool (like openai_chat.py)
            response = await fetch('https://api.openai.com/v1/responses', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
              },
              body: JSON.stringify({
                model: selectedModel,
                tools: [{ type: 'web_search' }],
                tool_choice: 'auto',
                input: newMessages[newMessages.length - 1].content,
              }),
            });

            if (!response.ok) {
              const errorData = await response.json();
              throw new Error(errorData.error?.message || 'API request failed');
            }

            const data = await response.json();
            console.log('Web search API response:', data);

            // Extract text - output_text is the direct property, or find it in output array
            let responseText = data.output_text;
            if (!responseText && data.output) {
              for (const item of data.output) {
                if (item.type === 'message' && item.content) {
                  for (const content of item.content) {
                    if (content.type === 'output_text' && content.text) {
                      responseText = content.text;
                      break;
                    }
                  }
                }
                if (responseText) break;
              }
            }

            assistantMessage = {
              role: 'assistant',
              content: responseText || 'No response from web search',
            };
          } else {
            // Standard Chat Completions API
            response = await fetch('https://api.openai.com/v1/chat/completions', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
              },
              body: JSON.stringify({
                model: selectedModel,
                max_tokens: 4096,
                messages: openaiMessages,
              }),
            });

            if (!response.ok) {
              const errorData = await response.json();
              throw new Error(errorData.error?.message || 'API request failed');
            }

            const data = await response.json();
            assistantMessage = {
              role: 'assistant',
              content: data.choices[0].message.content,
            };
          }
        } else {
          // Production (Vercel): use backend API
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              messages: openaiMessages,
              model: selectedModel,
              // Send either user's API key or access code for Stanley's key
              userApiKey: useSharedKey ? null : apiKey,
              accessCode: useSharedKey ? accessCode : null,
              webSearch: webSearchEnabled,
            }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'API request failed');
          }

          const data = await response.json();
          assistantMessage = {
            role: 'assistant',
            content: data.content,
          };
        }
      } else {
        // Anthropic API call
        const requestBody = {
          model: selectedModel,
          max_tokens: 4096,
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
        };

        if (systemPrompt) {
          requestBody.system = systemPrompt;
        }

        const response = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'anthropic-dangerous-direct-browser-access': 'true',
          },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error?.message || 'API request failed');
        }

        const data = await response.json();
        assistantMessage = {
          role: 'assistant',
          content: data.content[0].text,
        };
      }

      setMessages([...newMessages, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      setMessages([...newMessages, {
        role: 'assistant',
        content: `Error: ${error.message}`,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Clear chat
  const clearChat = () => {
    setMessages([]);
  };

  // Copy chat to clipboard
  const copyChat = async () => {
    if (messages.length === 0) {
      alert('No messages to copy');
      return;
    }

    const chatText = messages
      .map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
      .join('\n\n');

    try {
      await navigator.clipboard.writeText(chatText);
      alert('Chat copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Failed to copy chat');
    }
  };

  // Get total character count
  const getTotalCharCount = () => {
    return Object.values(loadedReports).reduce((sum, content) => sum + content.length, 0);
  };

  return (
    <div style={styles.container}>
      {/* Header / Sidebar */}
      <div style={styles.sidebar}>
        <h2 style={styles.sidebarTitle}>Report Chat</h2>

        {/* AI Provider Toggle */}
        <div style={styles.section}>
          <label style={styles.label}>AI Provider:</label>
          <div style={styles.providerToggle}>
            <button
              onClick={() => setAiProvider('ChatGPT')}
              style={{
                ...styles.providerBtn,
                ...(aiProvider === 'ChatGPT' ? styles.providerBtnActive : {}),
              }}
            >
              ChatGPT
            </button>
            <button
              onClick={() => setAiProvider('Anthropic')}
              style={{
                ...styles.providerBtn,
                ...(aiProvider === 'Anthropic' ? styles.providerBtnActive : {}),
              }}
            >
              Claude
            </button>
          </div>
          {/* Use Stanley's Key button - only for ChatGPT */}
          {aiProvider === 'ChatGPT' && (
            <button
              onClick={() => {
                const code = prompt("Enter access code for Stanley's key:");
                if (code) {
                  setAccessCode(code);
                  setUseSharedKey(true);
                  setApiKey(''); // Clear the API key field
                }
              }}
              style={{
                ...styles.button,
                marginTop: '8px',
                background: useSharedKey ? '#28a745' : '#6c757d',
              }}
            >
              {useSharedKey ? "✓ Using Stanley's Key" : "Use Stanley's Key"}
            </button>
          )}
        </div>

        {/* API Key Input */}
        <div style={styles.section}>
          <label style={styles.label}>{aiProvider === 'ChatGPT' ? 'OpenAI' : 'Anthropic'} API Key:</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={aiProvider === 'ChatGPT' ? 'sk-...' : 'sk-ant-...'}
            style={styles.input}
          />
        </div>

        {/* Model Selection */}
        <div style={styles.section}>
          <label style={styles.label}>{aiProvider === 'ChatGPT' ? 'OpenAI' : 'Claude'} Model:</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={styles.select}
          >
            {Object.entries(models).map(([name, id]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
        </div>

        {/* Web Search Toggle - Only for ChatGPT */}
        {aiProvider === 'ChatGPT' && (
          <div style={styles.section}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={webSearchEnabled}
                onChange={(e) => setWebSearchEnabled(e.target.checked)}
                style={styles.checkbox}
              />
              Enable Web Search
            </label>
          </div>
        )}

        {/* Role Selection */}
        <div style={styles.section}>
          <label style={styles.label}>Role:</label>
          <select
            value={selectedRole}
            onChange={async (e) => {
              const newRole = e.target.value;
              if (messages.length > 0) {
                if (window.confirm('Changing roles will clear the current chat.\n\nThe chat will be copied to your clipboard. Continue?')) {
                  // Copy chat to clipboard before clearing
                  const chatText = messages
                    .map(msg => `${msg.role === 'user' ? 'You' : 'Assistant'}: ${msg.content}`)
                    .join('\n\n');
                  try {
                    await navigator.clipboard.writeText(chatText);
                  } catch (err) {
                    console.error('Failed to copy chat:', err);
                  }
                  setSelectedRole(newRole);
                  setMessages([]);
                }
              } else {
                setSelectedRole(newRole);
              }
            }}
            style={styles.select}
          >
            {Object.entries(roles).map(([key, role]) => (
              <option key={key} value={key}>{role.name}</option>
            ))}
          </select>
        </div>

        {/* Preloaded Reports Section */}
        {preloadedFolders.length > 0 && (
          <div style={styles.section}>
            <label style={styles.label}>Preloaded Reports:</label>
            <select
              value={selectedPreloadedFolder}
              onChange={(e) => handlePreloadedFolderSelect(e.target.value)}
              style={styles.select}
              disabled={isLoadingPreloaded}
            >
              <option value="">-- Select a folder --</option>
              {preloadedFolders.map((folder) => (
                <option key={folder.name} value={folder.name}>
                  {folder.name} ({folder.fileCount} files)
                </option>
              ))}
            </select>
            {isLoadingPreloaded && (
              <p style={styles.charCount}>Loading...</p>
            )}
          </div>
        )}

        {/* Reports Section */}
        <div style={styles.section}>
          <label style={styles.label}>Upload Reports:</label>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFolderSelect}
            webkitdirectory=""
            directory=""
            multiple
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            style={styles.button}
          >
            Select Reports Folder
          </button>

          {Object.keys(loadedReports).length > 0 && (
            <>
              <button
                onClick={() => setIsReportsModalOpen(true)}
                style={{ ...styles.button, marginTop: '8px', background: '#28a745' }}
              >
                Edit Reports ({Object.keys(loadedReports).length})
              </button>
            </>
          )}
        </div>

        {/* Chat Actions */}
        <div style={styles.section}>
          <button
            onClick={copyChat}
            style={{ ...styles.button, background: '#28a745' }}
          >
            Copy Chat
          </button>
          <button
            onClick={clearChat}
            style={{ ...styles.button, marginTop: '8px', background: '#6c757d' }}
          >
            Clear Chat
          </button>
        </div>

        {/* View Mode Toggle */}
        {Object.keys(loadedReports).length > 0 && (
          <div style={styles.section}>
            <button
              onClick={() => setViewMode(viewMode === 'chat' ? 'viewer' : 'chat')}
              style={{ ...styles.button, background: viewMode === 'viewer' ? '#dc3545' : '#17a2b8' }}
            >
              {viewMode === 'viewer' ? 'Return to Chat' : 'Open Report Viewer'}
            </button>
          </div>
        )}

        {/* Literature Viewer Toggle */}
        {literatureFile && (
          <div style={styles.section}>
            <button
              onClick={() => setViewMode(viewMode === 'literature' ? 'chat' : 'literature')}
              style={{ ...styles.button, background: viewMode === 'literature' ? '#dc3545' : '#9b59b6' }}
            >
              {viewMode === 'literature' ? 'Return to Chat' : `📖 Open Literature`}
            </button>
            <p style={styles.charCount}>
              📖 {literatureFile}
            </p>
          </div>
        )}
      </div>

      {/* Literature Viewer Mode */}
      {viewMode === 'literature' && literatureFile ? (
        <div style={styles.literatureContainer}>
          {/* Literature Control Bar */}
          <div style={{
            ...styles.literatureControlBar,
            background: darkMode ? 'rgba(0, 0, 0, 0.8)' : '#e0e0e0',
          }}>
            <div style={styles.literatureTitle}>
              <span style={{ color: darkMode ? '#fff' : '#333' }}>
                📖 LITERATURE: {literatureFile}
              </span>
            </div>
            <div style={styles.literatureControls}>
              <div style={styles.literatureSearchRow}>
                <span style={{ color: darkMode ? '#aaa' : '#666', marginRight: '8px' }}>Search:</span>
                <input
                  type="text"
                  value={literatureSearchTerm}
                  onChange={(e) => setLiteratureSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchLiterature(0)}
                  placeholder="CHAPTER VIII, windmills..."
                  style={styles.literatureSearchInput}
                />
                <button onClick={() => searchLiterature(0)} style={styles.literatureGoBtn}>
                  Go
                </button>
                <button onClick={findPrevLiterature} style={styles.literaturePrevNextBtn}>
                  Prev
                </button>
                <button onClick={findNextLiterature} style={styles.literaturePrevNextBtn}>
                  Next
                </button>
              </div>
              <div style={styles.literatureLinesRow}>
                <span style={{ color: darkMode ? '#aaa' : '#666', marginRight: '8px' }}># of lines displayed:</span>
                <input
                  type="number"
                  value={literatureNumLines}
                  onChange={(e) => setLiteratureNumLines(parseInt(e.target.value) || 500)}
                  min="1"
                  max="5000"
                  style={styles.literatureLinesInput}
                />
                <button onClick={nextLinesLiterature} style={styles.literatureNextLinesBtn}>
                  Next Lines
                </button>
              </div>
            </div>
            <div style={styles.fontSizeControls}>
              <button
                style={styles.fontSizeBtn}
                onClick={() => changeFontSize(-2)}
                title="Decrease font size"
              >
                -
              </button>
              <button
                style={styles.fontSizeBtn}
                onClick={() => changeFontSize(2)}
                title="Increase font size"
              >
                +
              </button>
              <button
                style={styles.fontSizeBtn}
                onClick={() => setDarkMode(!darkMode)}
                title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
            </div>
          </div>

          {/* Found Line Info */}
          {literatureFoundLine && (
            <div style={{
              ...styles.literatureFoundInfo,
              background: darkMode ? '#2a4a2a' : '#d4edda',
              color: darkMode ? '#90EE90' : '#155724',
            }}>
              Found at line {literatureFoundLine}
            </div>
          )}

          {/* Literature Content Display */}
          <div
            ref={literatureContentRef}
            style={{
              ...styles.literatureContent,
              background: darkMode ? '#1a1a1a' : 'white',
            }}
          >
            {literatureDisplayContent ? (
              <pre style={{
                ...styles.literaturePreContent,
                fontSize: `${fontSize}px`,
                color: darkMode ? '#e0e0e0' : '#333',
              }}>
                {literatureDisplayContent}
              </pre>
            ) : (
              <div style={{
                ...styles.literatureEmptyState,
                color: darkMode ? '#888' : '#666',
              }}>
                <p>Enter a search term and click "Go" to find and display text from the literature.</p>
                <p style={{ fontSize: '14px', marginTop: '10px' }}>
                  Examples: "CHAPTER I", "CHAPTER VIII", "windmills", "Sancho"
                </p>
              </div>
            )}
          </div>

          {/* Copy Selection Button */}
          <div style={{
            ...styles.literatureFooter,
            background: darkMode ? 'rgba(0, 0, 0, 0.8)' : '#e0e0e0',
          }}>
            <button onClick={copySelection} style={styles.copySelectionBtn}>
              Copy Selection
            </button>
          </div>
        </div>
      ) : viewMode === 'viewer' && Object.keys(loadedReports).length > 0 ? (
        /* Text Viewer Mode */
        <div style={styles.viewerContainer}>
          {/* Report Thumbnails Sidebar */}
          <div style={{
            ...styles.thumbnailsSidebar,
            background: darkMode ? '#2a2a2a' : '#f5f5f5',
            borderRightColor: darkMode ? '#3a3a3a' : '#ddd',
          }}>
            <div style={{
              ...styles.thumbnailsHeader,
              background: darkMode ? '#1a1a2e' : '#e0e0e0',
              color: darkMode ? '#4da6ff' : '#333',
            }}>LOADED REPORTS</div>
            <div style={styles.thumbnailsSlider}>
              {Object.keys(loadedReports).map((filename, index) => (
                <div
                  key={filename}
                  style={{
                    ...styles.thumbnail,
                    ...(selectedReportKey === filename
                      ? { backgroundColor: darkMode ? '#3a3a3a' : '#d0d0d0' }
                      : {}),
                  }}
                  onClick={() => setSelectedReportKey(filename)}
                >
                  <div style={styles.thumbnailImageWrapper}>
                    <div style={{
                      ...styles.thumbnailPlaceholder,
                      background: isMarkdown(filename)
                        ? 'rgba(100,150,255,0.9)'
                        : darkMode ? 'rgba(60,60,60,0.9)' : 'rgba(255,255,255,0.9)',
                      color: isMarkdown(filename) ? 'white' : darkMode ? '#e0e0e0' : '#333',
                    }}>
                      {isMarkdown(filename) ? 'MD' : 'TXT'}
                    </div>
                  </div>
                  <div style={{
                    ...styles.thumbnailCaption,
                    color: darkMode ? '#e0e0e0' : '#333',
                  }}>{filename}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Main Viewer Area */}
          <div style={{
            ...styles.viewerMainArea,
            background: darkMode ? 'rgba(0, 0, 0, 0.75)' : '#f5f5f5',
          }}>
            {/* Control Bar */}
            <div style={{
              ...styles.viewerControlBar,
              background: darkMode ? 'rgba(0, 0, 0, 0.8)' : '#e0e0e0',
            }}>
              <span style={{
                ...styles.viewerTitle,
                color: darkMode ? '#fff' : '#333',
              }}>
                {selectedReportKey || 'Select a report'}
              </span>
              <div style={styles.fontSizeControls}>
                <button
                  style={styles.fontSizeBtn}
                  onClick={() => changeFontSize(-2)}
                  title="Decrease font size"
                >
                  -
                </button>
                <button
                  style={styles.fontSizeBtn}
                  onClick={() => changeFontSize(2)}
                  title="Increase font size"
                >
                  +
                </button>
                <button
                  style={styles.fontSizeBtn}
                  onClick={() => setDarkMode(!darkMode)}
                  title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                  {darkMode ? '☀️' : '🌙'}
                </button>
              </div>
            </div>

            {/* Content Display */}
            <div style={styles.viewerContent}>
              {selectedReportKey && loadedReports[selectedReportKey] ? (
                isMarkdown(selectedReportKey) ? (
                  <div
                    style={{
                      ...styles.markdownContent,
                      fontSize: `${fontSize}px`,
                      background: darkMode ? '#1a1a1a' : 'white',
                      color: darkMode ? '#e0e0e0' : '#333',
                    }}
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(loadedReports[selectedReportKey]) }}
                  />
                ) : (
                  <div style={{
                    ...styles.textContent,
                    fontSize: `${fontSize}px`,
                    background: darkMode ? '#1a1a1a' : 'white',
                    color: darkMode ? '#e0e0e0' : '#333',
                  }}>
                    <div style={{
                      ...styles.contentTitle,
                      color: darkMode ? '#4da6ff' : '#007acc',
                      borderBottomColor: darkMode ? '#4da6ff' : '#007acc',
                    }}>{selectedReportKey}</div>
                    <pre style={{
                      ...styles.preContent,
                      color: darkMode ? '#e0e0e0' : '#333',
                    }}>{loadedReports[selectedReportKey]}</pre>
                  </div>
                )
              ) : (
                <div style={{
                  ...styles.viewerEmptyState,
                  color: darkMode ? '#888' : '#666',
                }}>
                  <p>Select a report from the sidebar to view</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Main Chat Area */
        <div style={styles.mainArea}>
          {/* Info banner when reports loaded */}
          {Object.keys(loadedReports).length > 0 && (
            <div style={styles.infoBanner}>
              {getReportsForChat().length} of {Object.keys(loadedReports).length} report(s) sent to {aiProvider === 'ChatGPT' ? 'ChatGPT' : 'Claude'}
              {getExcludedFilesCount() > 0 && ` (${getExcludedFilesCount()} excluded - too large)`}
            </div>
          )}

          {/* Chat Messages */}
          <div ref={chatContainerRef} style={styles.chatContainer}>
            {messages.length === 0 ? (
              <div style={styles.emptyState}>
                <p>Load some reports and start chatting!</p>
                <p style={styles.emptyStateHint}>
                  Your reports will be included as context for {aiProvider === 'ChatGPT' ? 'ChatGPT' : 'Claude'} to reference.
                </p>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  style={{
                    ...styles.message,
                    ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage),
                  }}
                >
                  <div style={styles.messageRole}>
                    {msg.role === 'user' ? 'You' : (aiProvider === 'ChatGPT' ? 'ChatGPT' : 'Claude')}
                  </div>
                  <div style={styles.messageContent}>
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div style={{ ...styles.message, ...styles.assistantMessage }}>
                <div style={styles.messageRole}>{aiProvider === 'ChatGPT' ? 'ChatGPT' : 'Claude'}</div>
                <div style={styles.messageContent}>Thinking...</div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div style={styles.inputArea}>
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
              style={styles.textarea}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !inputValue.trim()}
              style={{
                ...styles.sendButton,
                opacity: isLoading || !inputValue.trim() ? 0.6 : 1,
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* Reports Modal */}
      {isReportsModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setIsReportsModalOpen(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>Loaded Reports</h3>
              <button
                onClick={() => setIsReportsModalOpen(false)}
                style={styles.okButton}
              >
                OK
              </button>
            </div>
            <div style={styles.modalContent}>
              {Object.keys(loadedReports).length === 0 ? (
                <p style={styles.noReports}>No reports loaded yet.</p>
              ) : (
                Object.entries(loadedReports).map(([filename, content]) => (
                  <div key={filename} style={styles.reportItem}>
                    <div style={styles.reportInfo}>
                      <span style={styles.reportName}>
                        {literatureFile === filename && '📖 *'}
                        {filename}
                        {literatureFile === filename && '*'}
                      </span>
                      <span style={styles.reportSize}>
                        ({content.length.toLocaleString()} chars)
                      </span>
                    </div>
                    <div style={styles.reportActions}>
                      <button
                        onClick={() => toggleLiterature(filename)}
                        style={literatureFile === filename ? styles.unsetLiteratureButton : styles.literatureButton}
                      >
                        {literatureFile === filename ? 'Unset' : '📖 Literature'}
                      </button>
                      <button
                        onClick={() => removeReport(filename)}
                        style={styles.removeButton}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
            {Object.keys(loadedReports).length > 0 && (
              <div style={styles.modalFooter}>
                <p style={styles.literatureNote}>
                  Note: "Literature" sets a file for the Literature Viewer (for reading large texts with search/navigation)
                </p>
                <button onClick={clearAllReports} style={styles.clearAllButton}>
                  Clear All Reports
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Styles
const styles = {
  container: {
    display: 'flex',
    height: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    background: '#f5f5f5',
  },
  sidebar: {
    width: '280px',
    background: '#1a1a2e',
    color: '#fff',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    overflowY: 'auto',
  },
  sidebarTitle: {
    margin: '0 0 10px 0',
    fontSize: '24px',
    fontWeight: '600',
    color: '#4da6ff',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  providerToggle: {
    display: 'flex',
    gap: '0',
    borderRadius: '6px',
    overflow: 'hidden',
  },
  providerBtn: {
    flex: 1,
    padding: '10px 12px',
    border: 'none',
    fontSize: '14px',
    fontWeight: '500',
    background: '#2d2d44',
    color: '#888',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  providerBtnActive: {
    background: '#4da6ff',
    color: '#fff',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: '#fff',
    cursor: 'pointer',
  },
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  },
  checkboxHint: {
    fontSize: '12px',
    color: '#888',
  },
  label: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#aaa',
  },
  input: {
    padding: '10px 12px',
    borderRadius: '6px',
    border: 'none',
    fontSize: '14px',
    background: '#2d2d44',
    color: '#fff',
  },
  select: {
    padding: '10px 12px',
    borderRadius: '6px',
    border: 'none',
    fontSize: '14px',
    background: '#2d2d44',
    color: '#fff',
    cursor: 'pointer',
  },
  button: {
    padding: '10px 16px',
    borderRadius: '6px',
    border: 'none',
    fontSize: '14px',
    fontWeight: '500',
    background: '#4da6ff',
    color: '#fff',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  charCount: {
    fontSize: '12px',
    color: '#888',
    margin: '4px 0 0 0',
  },
  mainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: '#fff',
  },
  infoBanner: {
    padding: '12px 20px',
    background: '#e8f4fd',
    color: '#1a73e8',
    fontSize: '14px',
    borderBottom: '1px solid #d0e3f0',
  },
  chatContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#666',
  },
  emptyStateHint: {
    fontSize: '14px',
    color: '#999',
  },
  message: {
    padding: '12px 16px',
    borderRadius: '12px',
    maxWidth: '80%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    background: '#4da6ff',
    color: '#fff',
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    background: '#f0f0f0',
    color: '#333',
  },
  messageRole: {
    fontSize: '12px',
    fontWeight: '600',
    marginBottom: '4px',
    opacity: 0.8,
  },
  messageContent: {
    fontSize: '14px',
    lineHeight: '1.5',
    whiteSpace: 'pre-wrap',
  },
  inputArea: {
    padding: '16px 20px',
    borderTop: '1px solid #e0e0e0',
    display: 'flex',
    gap: '12px',
    background: '#fafafa',
  },
  textarea: {
    flex: 1,
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid #ddd',
    fontSize: '14px',
    resize: 'none',
    minHeight: '50px',
    maxHeight: '150px',
    fontFamily: 'inherit',
  },
  sendButton: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    background: '#4da6ff',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    alignSelf: 'flex-end',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    background: '#fff',
    borderRadius: '12px',
    width: '500px',
    maxWidth: '90%',
    maxHeight: '80vh',
    display: 'flex',
    flexDirection: 'column',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #eee',
  },
  modalTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '600',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#666',
    padding: '0 8px',
  },
  okButton: {
    padding: '8px 20px',
    borderRadius: '6px',
    border: 'none',
    background: '#4da6ff',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  modalContent: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px',
  },
  noReports: {
    color: '#666',
    textAlign: 'center',
    padding: '20px',
  },
  reportItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    borderBottom: '1px solid #eee',
  },
  reportInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  reportName: {
    fontWeight: '500',
  },
  reportSize: {
    fontSize: '12px',
    color: '#888',
  },
  removeButton: {
    padding: '6px 12px',
    borderRadius: '4px',
    border: 'none',
    background: '#dc3545',
    color: '#fff',
    fontSize: '12px',
    cursor: 'pointer',
  },
  modalFooter: {
    padding: '16px 20px',
    borderTop: '1px solid #eee',
  },
  literatureNote: {
    fontSize: '12px',
    color: '#666',
    margin: '0 0 12px 0',
    fontStyle: 'italic',
  },
  clearAllButton: {
    width: '100%',
    padding: '10px',
    borderRadius: '6px',
    border: 'none',
    background: '#6c757d',
    color: '#fff',
    fontSize: '14px',
    cursor: 'pointer',
  },
  // Viewer styles
  viewerContainer: {
    flex: 1,
    display: 'flex',
    background: '#1a1a2e',
  },
  thumbnailsSidebar: {
    width: '250px',
    height: '100%',
    background: '#f5f5f5',
    borderRight: '1px solid #ddd',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
  },
  thumbnailsHeader: {
    padding: '15px 10px',
    background: '#1a1a2e',
    color: '#4da6ff',
    fontSize: '14px',
    fontWeight: 'bold',
    textAlign: 'center',
    borderBottom: '1px solid #333',
  },
  thumbnailsSlider: {
    display: 'flex',
    flexDirection: 'column',
    padding: '10px',
    flex: 1,
    overflowY: 'auto',
  },
  thumbnail: {
    cursor: 'pointer',
    padding: '8px 10px',
    borderRadius: '4px',
    transition: 'background-color 0.2s',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  thumbnailActive: {
    backgroundColor: '#d0d0d0',
  },
  thumbnailImageWrapper: {
    width: '40px',
    height: '40px',
    flexShrink: 0,
    borderRadius: '4px',
    overflow: 'hidden',
  },
  thumbnailPlaceholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 'bold',
    borderRadius: '4px',
  },
  thumbnailCaption: {
    fontSize: '13px',
    color: '#333',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    flex: 1,
  },
  viewerMainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(0, 0, 0, 0.75)',
  },
  viewerControlBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    background: 'rgba(0, 0, 0, 0.8)',
    padding: '15px 20px',
  },
  viewerTitle: {
    color: '#fff',
    fontSize: '16px',
    fontWeight: '500',
  },
  fontSizeControls: {
    display: 'flex',
    gap: '8px',
  },
  fontSizeBtn: {
    width: '40px',
    height: '40px',
    background: '#4da6ff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '18px',
    transition: 'all 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  viewerContent: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    justifyContent: 'center',
  },
  viewerEmptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#888',
    fontSize: '16px',
  },
  textContent: {
    maxWidth: '95%',
    width: '100%',
    background: 'white',
    color: '#333',
    padding: '40px',
    borderRadius: '10px',
    overflowY: 'auto',
    fontFamily: "'Courier New', monospace",
    lineHeight: '1.6',
    textAlign: 'left',
  },
  contentTitle: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#007acc',
    marginBottom: '20px',
    paddingBottom: '10px',
    borderBottom: '2px solid #007acc',
  },
  preContent: {
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word',
    margin: 0,
    fontFamily: 'inherit',
    fontSize: 'inherit',
  },
  markdownContent: {
    maxWidth: '95%',
    width: '100%',
    background: 'white',
    color: '#333',
    padding: '40px',
    borderRadius: '10px',
    overflowY: 'auto',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif",
    lineHeight: '1.6',
    textAlign: 'left',
  },
  // Report modal action buttons
  reportActions: {
    display: 'flex',
    gap: '8px',
  },
  literatureButton: {
    padding: '6px 12px',
    borderRadius: '4px',
    border: 'none',
    background: '#9b59b6',
    color: '#fff',
    fontSize: '12px',
    cursor: 'pointer',
  },
  unsetLiteratureButton: {
    padding: '6px 12px',
    borderRadius: '4px',
    border: 'none',
    background: '#6c757d',
    color: '#fff',
    fontSize: '12px',
    cursor: 'pointer',
  },
  // Literature viewer styles
  literatureContainer: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: '#1a1a2e',
  },
  literatureControlBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '12px',
    padding: '15px 20px',
  },
  literatureTitle: {
    fontSize: '16px',
    fontWeight: '500',
  },
  literatureControls: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  literatureSearchRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  literatureSearchInput: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#2d2d44',
    color: '#fff',
    fontSize: '14px',
    width: '250px',
  },
  literatureGoBtn: {
    padding: '8px 16px',
    borderRadius: '4px',
    border: 'none',
    background: '#9b59b6',
    color: '#fff',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  literaturePrevNextBtn: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: 'none',
    background: '#4da6ff',
    color: '#fff',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  literatureLinesRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  literatureLinesInput: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#2d2d44',
    color: '#fff',
    fontSize: '14px',
    width: '80px',
  },
  literatureNextLinesBtn: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: 'none',
    background: '#28a745',
    color: '#fff',
    fontSize: '14px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  literatureFoundInfo: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '500',
  },
  literatureContent: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    margin: '0 20px',
    borderRadius: '8px',
  },
  literaturePreContent: {
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word',
    margin: 0,
    fontFamily: "'Georgia', 'Times New Roman', serif",
    lineHeight: '1.8',
  },
  literatureEmptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    textAlign: 'center',
    fontSize: '16px',
  },
  literatureFooter: {
    padding: '15px 20px',
    display: 'flex',
    justifyContent: 'center',
  },
  copySelectionBtn: {
    padding: '10px 24px',
    borderRadius: '6px',
    border: 'none',
    background: '#28a745',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
};

export default ReportChat;
