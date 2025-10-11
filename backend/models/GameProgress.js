const mongoose = require("mongoose");
const { Schema } = mongoose;

const matchSchema = new Schema({
  match: Number,
  score: Number,
  correct: Number,
  incorrect: Number,
  totalQuestions: Number,
  averageScore: Number,
});

const gameHistorySchema = new Schema({
  date: { type: String, required: true },
  TotalMatches: Number,
  TotalAverageScore: Number,
  matches: [matchSchema],
});

const gameProgressSchema = new Schema({
  userId: { type: Schema.Types.ObjectId, ref: "User", required: true },
  games: {
    type: Map,
    of: [gameHistorySchema],
    default: {},
  },
});

module.exports =
  mongoose.models.GameProgress ||
  mongoose.model("GameProgress", gameProgressSchema);
