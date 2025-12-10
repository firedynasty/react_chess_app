c() {
    # Enhanced c() function with navigation validation AND file opening
    # cv = "c validated" - checks if navigation reached the intended destination
    # -t flag prints directory/file paths instead of using fzf (for copy/paste)
    # Can now open files if the target is a file instead of a directory
    
    local original_dir="$PWD"
    local intended_target=""
    local validation_mode="partial"  # "exact" or "partial"
    local text_output=false
    
    # Helper function to open a file using appropriate command
    open_file() {
        local file_path="$1"
        
        if [[ ! -f "$file_path" ]]; then
            echo "✗ File does not exist: $file_path"
            return 1
        fi
        
        echo "Opening file: $file_path"
        
        # Detect OS and use appropriate open command
        case "$(uname -s)" in
            Darwin*)
                # macOS
                open "$file_path"
                ;;
            Linux*)
                # Linux - try xdg-open first, then fallback options
                if command -v xdg-open &> /dev/null; then
                    xdg-open "$file_path" &> /dev/null &
                elif command -v gnome-open &> /dev/null; then
                    gnome-open "$file_path" &> /dev/null &
                elif command -v kde-open &> /dev/null; then
                    kde-open "$file_path" &> /dev/null &
                else
                    echo "✗ No suitable file opener found. Install xdg-open or specify a default editor."
                    return 1
                fi
                ;;
            CYGWIN*|MINGW*|MSYS*)
                # Windows
                start "$file_path"
                ;;
            *)
                echo "✗ Unsupported operating system"
                return 1
                ;;
        esac
        
        return 0
    }
    
    # Smart deep search function for fallback - progressive depth with early termination
    # Searches for directories by default, or files if search term suggests a file
    deep_search() {
        local search_term="$1"
        local search_dirs=("${@:2}")
        
        # Check if we're in text output mode by checking parent function variable
        local use_text_output="$text_output"
        
        # Determine if we should search for files based on the search term
        local search_files=false
        if [[ "$search_term" == *.* ]]; then
            search_files=true
        fi
        
        # If no directories specified, use current directory
        if [ ${#search_dirs[@]} -eq 0 ]; then
            search_dirs=(".")
        fi
        
        # Validate directories
        local valid_dirs=()
        for dir in "${search_dirs[@]}"; do
            if [ -d "$dir" ]; then
                valid_dirs+=("$dir")
            else
                echo "Warning: $dir is not a directory"
            fi
        done
        
        if [ ${#valid_dirs[@]} -eq 0 ]; then
            echo "No valid directories provided."
            return 1
        fi
        
        if [ "$search_files" = true ]; then
            echo "Smart searching for \"$search_term\" (files and directories) in ${search_dirs[@]}..."
        else
            echo "Smart searching for \"$search_term\" in ${search_dirs[@]}..."
        fi
        
        # Strategy: Progressive depth search with early termination
        local dir_results=""
        local file_results=""
        local found_at_depth=0
        
        for depth in 1 2 3 4; do
            local depth_dir_results=""
            local depth_file_results=""
            
            for dir in "${valid_dirs[@]}"; do
                [ -d "$dir" ] || continue
                
                # Always search for directories
                local dir_matches=$(find "$dir" -maxdepth $depth -mindepth $depth -type d -iname "*$search_term*" 2>/dev/null)
                if [ -n "$dir_matches" ]; then
                    if [ -n "$depth_dir_results" ]; then
                        depth_dir_results="$depth_dir_results
$dir_matches"
                    else
                        depth_dir_results="$dir_matches"
                    fi
                fi
                
                # Only search for files if the search term suggests a file
                if [ "$search_files" = true ]; then
                    local file_matches=$(find "$dir" -maxdepth $depth -mindepth $depth -type f -iname "*$search_term*" 2>/dev/null)
                    if [ -n "$file_matches" ]; then
                        if [ -n "$depth_file_results" ]; then
                            depth_file_results="$depth_file_results
$file_matches"
                        else
                            depth_file_results="$file_matches"
                        fi
                    fi
                fi
            done
            
            if [ -n "$depth_dir_results" ] || [ -n "$depth_file_results" ]; then
                if [ -n "$depth_dir_results" ]; then
                    if [ -n "$dir_results" ]; then
                        dir_results="$dir_results
$depth_dir_results"
                    else
                        dir_results="$depth_dir_results"
                    fi
                fi
                
                if [ -n "$depth_file_results" ]; then
                    if [ -n "$file_results" ]; then
                        file_results="$file_results
$depth_file_results"
                    else
                        file_results="$depth_file_results"
                    fi
                fi
                
                if [ $found_at_depth -eq 0 ]; then
                    found_at_depth=$depth
                fi
                
                # Stop if we found enough results or if this is getting too deep
                local current_count=$(($(echo "$dir_results" | grep -c .) + $(echo "$file_results" | grep -c .)))
                if [ $current_count -gt 10 ] || [ $depth -gt 3 ]; then
                    echo "Found $current_count results (stopping at depth $depth)"
                    break
                fi
            fi
        done
        
        # Combine results (directories first, then files)
        local all_results=""
        if [ -n "$dir_results" ]; then
            all_results="$dir_results"
        fi
        if [ -n "$file_results" ]; then
            if [ -n "$all_results" ]; then
                all_results="$all_results
$file_results"
            else
                all_results="$file_results"
            fi
        fi
        
        # Count matches
        local matches
        if [ -n "$all_results" ]; then
            matches=$(echo "$all_results" | wc -l)
            matches=$(echo $matches)
        else
            matches=0
        fi
        
        if [ "$matches" -eq 0 ]; then
            if [ "$search_files" = true ]; then
                echo "No matching files or directories found."
            else
                echo "No matching directories found."
            fi
            return 1
        elif [ "$matches" -eq 1 ]; then
            # Exactly one match - handle it appropriately
            if [ "$use_text_output" = true ]; then
                echo "$all_results"
                return 0
            else
                # Check if it's a file or directory
                if [ -f "$all_results" ]; then
                    open_file "$all_results"
                elif [ -d "$all_results" ]; then
                    cd "$all_results"
                    echo "Changed to: $all_results"
                    echo "Listing files in $(basename "$PWD"):"
                    echo "can use trees to use tree -d ..."
                    ls -1
                fi
            fi
        else
            # Multiple matches - use fzf or print text based on flag
            echo "Found $matches matching items:"
            if [ "$use_text_output" = true ]; then
                # Print numbered list for copy/paste
                echo "$all_results" | head -20 | sort | nl -n ln -w2
                return 0
            else
                # Use fzf for interactive selection with preview
                local selected=$(echo "$all_results" | head -20 | sort | nl -n ln -w2 | fzf --height 40% --reverse | awk '{$1=""; sub(/^ /, ""); print}')
                if [ -n "$selected" ]; then
                    # Check if it's a file or directory
                    if [ -f "$selected" ]; then
                        open_file "$selected"
                    elif [ -d "$selected" ]; then
                        cd "$selected"
                        echo "Changed to: $selected"
                        echo "Listing files in $(basename "$PWD"):"
                        echo "can use trees to use tree -d ..."
                        ls -1
                    fi
                else
                    echo "No item selected."
                    return 1
                fi
            fi
        fi
    }
    
    # Helper function to validate navigation
    validate_navigation() {
        local intended="$1"
        local current="$PWD"
        local mode="$2"
        
        if [[ "$mode" == "exact" ]]; then
            # Exact match validation
            if [[ "$current" == "$intended" ]]; then
                echo "✓ Successfully navigated to: $current"
                return 0
            else
                echo "✗ Navigation failed. Expected: $intended, Got: $current"
                return 1
            fi
        else
            # Partial match validation (default)
            local current_basename=$(/usr/bin/basename "$current")
            local intended_basename=$(/usr/bin/basename "$intended")
            
            if [[ "$current" == "$intended" ]]; then
                echo "✓ Successfully navigated to: $current"
                return 0
            elif [[ "$current_basename" == "$intended_basename" ]]; then
                echo "✓ Successfully navigated to: $current (basename match)"
                return 0
            elif [[ "$current" == *"$intended_basename"* || "$current_basename" == *"$intended_basename"* ]]; then
                echo "✓ Successfully navigated to: $current (partial match)"
                return 0
            else
                echo "✗ Navigation validation failed. Expected something matching '$intended_basename', Got: $current"
                return 1
            fi
        fi
    }
    
    # Helper function to perform validated cd
    validated_cd() {
        local target="$1"
        local description="$2"
        local old_pwd="$PWD"
        
        if [[ -d "$target" ]]; then
            cd "$target"
            if [[ $? -eq 0 ]]; then
                echo "Changed to: $target ($description)"
                return 0
            else
                echo "✗ Failed to change to: $target"
                return 1
            fi
        else
            echo "✗ Directory does not exist: $target"
            return 1
        fi
    }
    
    # Parse arguments for -t flag (supports both 'c -t project' and 'c project -t')
    local search_term=""
    if [[ "$1" == "-t" ]]; then
        text_output=true
        search_term="$2"
    elif [[ "$2" == "-t" ]]; then
        text_output=true
        search_term="$1"
    else
        search_term="$1"
    fi
    
    # Handle comma-separated navigation (directories only, no file opening in chain)
    if [[ "$search_term" == *","* ]]; then
        local input="$search_term"
        local current_dir="$PWD"
        local navigation_path=""
        
        # Process comma-separated parts
        while [[ "$input" == *","* ]]; do
            local part="${input%%,*}"
            input="${input#*,}"
            part=$(echo "$part" | tr -d '[:space:]')
            
            echo "Processing: $part"
            navigation_path+="$part → "
            
            # Skip deep search patterns (not supported in cv)
            if [[ "$part" == -* ]]; then
                echo "✗ Deep search patterns (starting with -) are not supported in cv()"
                cd "$current_dir"
                return 1
            fi
            
            # Handle special directories
            case "$part" in
                "documents")
                    if validated_cd "$HOME/Documents" "Documents shortcut"; then
                        validate_navigation "Documents" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "desktop")
                    if validated_cd "$HOME/Desktop" "Desktop shortcut"; then
                        validate_navigation "Desktop" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "downloads")
                    if validated_cd "$HOME/Downloads" "Downloads shortcut"; then
                        validate_navigation "Downloads" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "music")
                    if validated_cd "$HOME/Music" "Music shortcut"; then
                        validate_navigation "Music" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "python")
                    if [[ -d "./46-python" ]]; then
                        if validated_cd "./46-python" "Python directory"; then
                            validate_navigation "python" "partial"
                        else
                            cd "$current_dir"
                            return 1
                        fi
                    else
                        echo "✗ Python directory not found in current location"
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "onedrive")
                    # Simple OneDrive path check
                    if [[ -d "$HOME/OneDrive" ]]; then
                        if validated_cd "$HOME/OneDrive" "OneDrive shortcut"; then
                            echo "✓ Successfully navigated to: $HOME/OneDrive"
                        else
                            cd "$current_dir"
                            return 1
                        fi
                    elif [[ -d "$HOME/Library/CloudStorage/OneDrive-Personal" ]]; then
                        if validated_cd "$HOME/Library/CloudStorage/OneDrive-Personal" "OneDrive shortcut"; then
                            echo "✓ Successfully navigated to: $HOME/Library/CloudStorage/OneDrive-Personal"
                        else
                            cd "$current_dir"
                            return 1
                        fi
                    else
                        echo "✗ OneDrive directory not found"
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                *)
                    # Try to find matching directory
                    local target_found=false
                    
                    if [[ -d ./*-"$part"*/ ]]; then
                        local target_dir=(./*-"$part"*/)
                        if validated_cd "$target_dir" "numbered pattern match for '$part'"; then
                            validate_navigation "$part" "partial"
                            target_found=true
                        fi
                    elif [[ -d ./"$part"/ ]]; then
                        if validated_cd "./$part" "exact match for '$part'"; then
                            validate_navigation "$part" "partial"
                            target_found=true
                        fi
                    fi
                    
                    if [[ "$target_found" == false ]]; then
                        echo "✗ No directory matching '$part' found"
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
            esac
        done
        
        # Process final part
        local part=$(echo "$input" | tr -d '[:space:]')
        if [[ -n "$part" ]]; then
            echo "Processing final part: $part"
            navigation_path+="$part"
            
            # Skip deep search patterns for final part too
            if [[ "$part" == -* ]]; then
                echo "✗ Deep search patterns (starting with -) are not supported in cv()"
                cd "$current_dir"
                return 1
            fi
            
            # Handle special directories for final part
            case "$part" in
                "documents")
                    if validated_cd "$HOME/Documents" "Documents shortcut"; then
                        validate_navigation "Documents" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "desktop")
                    if validated_cd "$HOME/Desktop" "Desktop shortcut"; then
                        validate_navigation "Desktop" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "downloads")
                    if validated_cd "$HOME/Downloads" "Downloads shortcut"; then
                        validate_navigation "Downloads" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "music")
                    if validated_cd "$HOME/Music" "Music shortcut"; then
                        validate_navigation "Music" "partial"
                    else
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "python")
                    if [[ -d "./46-python" ]]; then
                        if validated_cd "./46-python" "Python directory"; then
                            validate_navigation "python" "partial"
                        else
                            cd "$current_dir"
                            return 1
                        fi
                    else
                        echo "✗ Python directory not found in current location"
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                "onedrive")
                    # Simple OneDrive path check
                    if [[ -d "$HOME/OneDrive" ]]; then
                        if validated_cd "$HOME/OneDrive" "OneDrive shortcut"; then
                            echo "✓ Successfully navigated to: $HOME/OneDrive"
                        else
                            cd "$current_dir"
                            return 1
                        fi
                    elif [[ -d "$HOME/Library/CloudStorage/OneDrive-Personal" ]]; then
                        if validated_cd "$HOME/Library/CloudStorage/OneDrive-Personal" "OneDrive shortcut"; then
                            echo "✓ Successfully navigated to: $HOME/Library/CloudStorage/OneDrive-Personal"
                        else
                            cd "$current_dir"
                            return 1
                        fi
                    else
                        echo "✗ OneDrive directory not found"
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
                *)
                    # Try to find matching directory
                    local target_found=false
                    
                    if [[ -d ./*-"$part"*/ ]]; then
                        local target_dir=(./*-"$part"*/)
                        if validated_cd "$target_dir" "numbered pattern match for '$part'"; then
                            validate_navigation "$part" "partial"
                            target_found=true
                        fi
                    elif [[ -d ./"$part"/ ]]; then
                        if validated_cd "./$part" "exact match for '$part'"; then
                            validate_navigation "$part" "partial"
                            target_found=true
                        fi
                    fi
                    
                    if [[ "$target_found" == false ]]; then
                        echo "✗ No directory matching '$part' found"
                        cd "$current_dir"
                        return 1
                    fi
                    ;;
            esac
        fi
        
        echo "✓ Navigation path completed: $navigation_path"
        echo "Final destination: $PWD"
        echo "Listing files in $(/usr/bin/basename "$PWD"):"
        /bin/ls -1
        return 0
    fi
    
    # Handle single argument cases (or -t flag with no search term)
    if [[ $# -eq 0 ]] || ([[ "$1" == "-t" ]] && [[ -z "$2" ]]) || [[ "$1" == "-t" && $# -eq 1 ]]; then
        if [[ "$text_output" == true ]]; then
            echo "$HOME"
            return 0
        else
            intended_target="$HOME"
            if validated_cd "$HOME" "home directory"; then
                validate_navigation "$HOME" "exact"
            else
                return 1
            fi
        fi
    else
        case "$search_term" in
            "documents")
                if [[ "$text_output" == true ]]; then
                    echo "$HOME/Documents"
                    return 0
                else
                    intended_target="$HOME/Documents"
                    if validated_cd "$HOME/Documents" "Documents shortcut"; then
                        validate_navigation "Documents" "partial"
                    else
                        return 1
                    fi
                fi
                ;;
            "desktop")
                if [[ "$text_output" == true ]]; then
                    echo "$HOME/Desktop"
                    return 0
                else
                    intended_target="$HOME/Desktop"
                    if validated_cd "$HOME/Desktop" "Desktop shortcut"; then
                        validate_navigation "Desktop" "partial"
                    else
                        return 1
                    fi
                fi
                ;;
            "downloads")
                if [[ "$text_output" == true ]]; then
                    echo "$HOME/Downloads"
                    return 0
                else
                    intended_target="$HOME/Downloads"
                    if validated_cd "$HOME/Downloads" "Downloads shortcut"; then
                        validate_navigation "Downloads" "partial"
                    else
                        return 1
                    fi
                fi
                ;;
            "music")
                if [[ "$text_output" == true ]]; then
                    echo "$HOME/Music"
                    return 0
                else
                    intended_target="$HOME/Music"
                    if validated_cd "$HOME/Music" "Music shortcut"; then
                        validate_navigation "Music" "partial"
                    else
                        return 1
                    fi
                fi
                ;;
            "onedrive")
                # Simple OneDrive path check
                if [[ -d "$HOME/OneDrive" ]]; then
                    if [[ "$text_output" == true ]]; then
                        echo "$HOME/OneDrive"
                        return 0
                    else
                        intended_target="$HOME/OneDrive"
                        if validated_cd "$HOME/OneDrive" "OneDrive shortcut"; then
                            echo "✓ Successfully navigated to: $HOME/OneDrive"
                        else
                            return 1
                        fi
                    fi
                elif [[ -d "$HOME/Library/CloudStorage/OneDrive-Personal" ]]; then
                    if [[ "$text_output" == true ]]; then
                        echo "$HOME/Library/CloudStorage/OneDrive-Personal"
                        return 0
                    else
                        intended_target="$HOME/Library/CloudStorage/OneDrive-Personal"
                        if validated_cd "$HOME/Library/CloudStorage/OneDrive-Personal" "OneDrive shortcut"; then
                            echo "✓ Successfully navigated to: $HOME/Library/CloudStorage/OneDrive-Personal"
                        else
                            return 1
                        fi
                    fi
                else
                    echo "✗ OneDrive directory not found"
                    return 1
                fi
                ;;
            *)
                # NEW: Check if it's a file first
                if [[ -f "$search_term" ]]; then
                    # It's a file - open it
                    if [[ "$text_output" == true ]]; then
                        echo "$search_term"
                        return 0
                    else
                        open_file "$search_term"
                        return $?
                    fi
                # Try direct directory
                elif [[ -d "$search_term" ]]; then
                    if [[ "$text_output" == true ]]; then
                        echo "$search_term"
                        return 0
                    else
                        intended_target="$search_term"
                        if validated_cd "$search_term" "direct directory match"; then
                            validate_navigation "$search_term" "partial"
                        else
                            return 1
                        fi
                    fi
                elif [[ -d ./*-"$search_term"*/ ]]; then
                    local target_dir=(./*-"$search_term"*/)
                    if [[ "$text_output" == true ]]; then
                        echo "$target_dir"
                        return 0
                    else
                        intended_target="$target_dir"
                        if validated_cd "$target_dir" "numbered pattern match"; then
                            validate_navigation "$search_term" "partial"
                        else
                            return 1
                        fi
                    fi
                else
                    # Fuzzy search with validation (case-insensitive)
                    # Only search for directories by default; search files if term contains "."
                    local dir_matches=$(find . -maxdepth 1 -type d -ipath "*$search_term*" 2>/dev/null | sort)
                    local file_matches=""
                    
                    # Only search for files if the search term suggests it's a file (contains a dot)
                    if [[ "$search_term" == *.* ]]; then
                        file_matches=$(find . -maxdepth 1 -type f -iname "*$search_term*" 2>/dev/null | sort)
                    fi
                    
                    # Combine matches (directories first)
                    local all_matches=""
                    if [[ -n "$dir_matches" ]]; then
                        all_matches="$dir_matches"
                    fi
                    if [[ -n "$file_matches" ]]; then
                        if [[ -n "$all_matches" ]]; then
                            all_matches="$all_matches
$file_matches"
                        else
                            all_matches="$file_matches"
                        fi
                    fi
                    
                    local count=$(echo "$all_matches" | grep -v "^$" | wc -l | tr -d '[:space:]')
                    
                    if [[ $count -eq 1 ]]; then
                        if [[ "$text_output" == true ]]; then
                            echo "$all_matches"
                            return 0
                        else
                            # Check if it's a file or directory
                            if [[ -f "$all_matches" ]]; then
                                open_file "$all_matches"
                                return $?
                            else
                                intended_target="$all_matches"
                                if validated_cd "$all_matches" "fuzzy match"; then
                                    validate_navigation "$search_term" "partial"
                                else
                                    return 1
                                fi
                            fi
                        fi
                    elif [[ $count -gt 1 ]]; then
                        echo "Found $count matching items."
                        if [[ "$text_output" == true ]]; then
                            # Print numbered list for copy/paste
                            echo "$all_matches" | nl -n ln -w2
                            return 0
                        else
                            echo "Select one:"
                            local selected=$(echo "$all_matches" | fzf --height 40% --reverse)
                            if [[ -n "$selected" ]]; then
                                # Check if it's a file or directory
                                if [[ -f "$selected" ]]; then
                                    open_file "$selected"
                                    return $?
                                else
                                    intended_target="$selected"
                                    if validated_cd "$selected" "user selection"; then
                                        validate_navigation "$search_term" "partial"
                                    else
                                        return 1
                                    fi
                                fi
                            else
                                echo "✗ No item selected"
                                return 1
                            fi
                        fi
                    else
                        echo "✗ No directories matching '$search_term' found"
                        echo "Falling back to deep search..."
                        if [[ "$text_output" == true ]]; then
                            # Pass text_output flag to deep_search function
                            deep_search "$search_term" "." && return 0 || return 1
                        else
                            deep_search "$search_term"
                            return $?
                        fi
                    fi
                fi
                ;;
        esac
    fi
    
    # Only show file listing if not in text output mode AND we navigated to a directory
    if [[ "$text_output" != true ]] && [[ -d "$PWD" ]]; then
        echo "Listing files in $(/usr/bin/basename "$PWD"):"
        /bin/ls -1
    fi
    return 0
}