const express = require("express");
const GameProgress = require("../models/GameProgress");

const router = express.Router();


// Save game progress (entire history)
router.post("/save", async (req, res) => {
  try {
    const { userId, gameName, gameHistory } = req.body; // ✅ gameHistory = full array

    let progress = await GameProgress.findOne({ userId });
    if (!progress) {
      progress = new GameProgress({ userId, games: {} });
    }

    // Replace old history with new one
    progress.games.set(gameName, gameHistory);

    await progress.save();

    res.json({ success: true, data: progress });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get game progress
router.get("/:userId/:gameName", async (req, res) => {
  try {
    const { userId, gameName } = req.params;
    const progress = await GameProgress.findOne({ userId });

    if (!progress || !progress.games.has(gameName)) {
      return res.json({ success: true, data: [] });
    }

    res.json({ success: true, data: progress.games.get(gameName) });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
