() => {
    /**
     * Convert formatted like count string to number
     * Handles formats like "10+", "1千+", "1万+" (Chinese numerals)
     */
    const parseLikeCount = (countStr) => {
        if (!countStr || countStr.trim() === "") return -1;

        let count = countStr.trim();
        // Remove '+' if present
        const hasPlus = count.endsWith("+");
        if (hasPlus) {
            count = count.slice(0, -1);
        }

        // Handle Chinese numerals
        if (count.includes("千")) {
            // 千 = thousand
            return parseFloat(count.replace("千", "")) * 1000;
        } else if (count.includes("万")) {
            // 万 = ten thousand
            return parseFloat(count.replace("万", "")) * 10000;
        } else {
            return parseFloat(count) || -1;
        }
    };

    const results = [];

    // Get note results
    const notes = document.querySelectorAll("section.note-item");
    for (const note of notes) {
        try {
            const link = note.querySelector(
                'a.cover[href*="/explore/"], a.cover[href*="/search_result/"]'
            );
            const url = link?.href || "";
            if (!url) {
                continue;
            }

            const coverImgEl = note.querySelector("img");

            // Get title and author
            const titleEl = note.querySelector(".title");
            const authorEl = note.querySelector(".author-wrapper .name");
            const likeCountEl = note.querySelector(".count");

            results.push({
                title: titleEl?.textContent?.trim() || "",
                url: url,
                author: authorEl?.textContent?.trim() || "",
                like_count: likeCountEl?.textContent?.trim() || "",
                like_count_num: parseLikeCount(likeCountEl?.textContent),
                is_video: !!link?.querySelector(".play-icon"),
                cover_url: coverImgEl?.src || "",
            });
        } catch (e) {
            console.error("Error processing note:", e);
        }
    }

    const videoCount = results.filter((r) => r.is_video).length;
    console.log(`Found ${results.length} total results (${videoCount} videos)`);
    return results;
}