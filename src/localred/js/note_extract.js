() => {
    const result = {
        author: '',
        title: '',
        content: '',
        date: '',
        comments: [],
    };

    // Helper function to extract and normalize date from various formats
    const extractDate = (dateStr) => {
        if (!dateStr) return '';
        
        // Try to extract YYYY-MM-DD format
        const fullDateMatch = dateStr.match(/(\d{4})-(\d{1,2})-(\d{1,2})/);
        if (fullDateMatch) {
            const [_, year, month, day] = fullDateMatch;
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        }
        
        // Try to extract MM-DD format (without year)
        const partialDateMatch = dateStr.match(/(\d{1,2})-(\d{1,2})/);
        if (partialDateMatch) {
            const [_, month, day] = partialDateMatch;
            // Use current year as fallback
            const year = new Date().getFullYear();
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        }
        
        // Return original if no pattern matched
        return dateStr;
    };

    try {
        // try get note title
        const titleEl = document.querySelector('.title');
        if (titleEl) {
            result.title = titleEl.textContent.trim();
        }

        // try get note author
        const authorEl = document.querySelector('.author-wrapper .username');
        if (authorEl) {
            result.author = authorEl.textContent.trim();
        }

        // try get note content
        const noteContent = document.querySelector('.note-content');
        if (noteContent) {
            // Remove date elements before getting text content
            const dateElements = noteContent.querySelectorAll('.date');
            dateElements.forEach(el => {
                if (!result.date) {
                    const rawDate = el.textContent.trim();
                    result.date = extractDate(rawDate);
                }
                el.remove();
            });
            result.content = noteContent.textContent.trim();
        }

        // try get note comments
        const commentEl = document.querySelector('.comments-el');
        const commentItems = commentEl.querySelectorAll('.comment-item');
        commentItems.forEach(item => {
            const authorElement = item.querySelector('.author .name');
            const contentElement = item.querySelector('.content .note-text');

            if (authorElement && contentElement) {
                const author = authorElement.textContent.trim();
                const content = contentElement.textContent.trim();

                // filter author by name
                if (author === result.author) {
                    return;
                }
                // filter empty
                if (content === '') {
                    return;
                }

                result.comments.push(`${author}: ${content}`);
            }
        });

    } catch (e) {
        console.error('Error processing note:', e);
    }
    
    return result;
}