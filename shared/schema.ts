import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  displayName: text("display_name").notNull(),
  avatar: text("avatar"),
  color: text("color").notNull().default("#2864FF"),
  homeCity: text("home_city"),
});

export const trips = pgTable("trips", {
  id: serial("id").primaryKey(),
  tripId: text("trip_id").notNull().unique(),
  title: text("title").notNull(),
  destination: text("destination"),
  startDate: timestamp("start_date"),
  endDate: timestamp("end_date"),
  budget: integer("budget"),
  state: text("state").notNull().default("INIT"),
  inviteToken: text("invite_token").notNull().unique(),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const tripParticipants = pgTable("trip_participants", {
  id: serial("id").primaryKey(),
  tripId: text("trip_id").notNull(),
  userId: integer("user_id").notNull(),
  role: text("role").notNull().default("traveler"),
  isOnline: boolean("is_online").default(false),
  joinedAt: timestamp("joined_at").defaultNow(),
  hasSubmittedPreferences: boolean("has_submitted_preferences").default(false),
  hasSubmittedAvailability: boolean("has_submitted_availability").default(false),
});

export const messages = pgTable("messages", {
  id: serial("id").primaryKey(),
  tripId: text("trip_id").notNull(),
  userId: integer("user_id"),
  type: text("type").notNull().default("user"), // user, agent, system
  content: text("content").notNull(),
  metadata: jsonb("metadata"),
  timestamp: timestamp("timestamp").defaultNow(),
});

export const dateAvailability = pgTable("date_availability", {
  id: serial("id").primaryKey(),
  tripId: text("trip_id").notNull(),
  userId: integer("user_id").notNull(),
  date: timestamp("date").notNull(),
  available: boolean("available").notNull().default(true),
});

export const votes = pgTable("votes", {
  id: serial("id").primaryKey(),
  tripId: text("trip_id").notNull(),
  userId: integer("user_id").notNull(),
  optionId: text("option_id").notNull(),
  emoji: text("emoji").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
});

export const tripOptions = pgTable("trip_options", {
  id: serial("id").primaryKey(),
  tripId: text("trip_id").notNull(),
  optionId: text("option_id").notNull().unique(),
  type: text("type").notNull(), // itinerary, flight, hotel, activity
  title: text("title").notNull(),
  description: text("description"),
  price: integer("price"),
  image: text("image"),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
  displayName: true,
  avatar: true,
  color: true,
  homeCity: true,
});

export const insertTripSchema = createInsertSchema(trips).pick({
  tripId: true,
  title: true,
  destination: true,
  startDate: true,
  endDate: true,
  budget: true,
  state: true,
});

export const insertMessageSchema = createInsertSchema(messages).pick({
  tripId: true,
  userId: true,
  type: true,
  content: true,
  metadata: true,
});

export const insertVoteSchema = createInsertSchema(votes).pick({
  tripId: true,
  userId: true,
  optionId: true,
  emoji: true,
});

export const insertTripOptionSchema = createInsertSchema(tripOptions).pick({
  tripId: true,
  optionId: true,
  type: true,
  title: true,
  description: true,
  price: true,
  image: true,
  metadata: true,
});

export const insertDateAvailabilitySchema = createInsertSchema(dateAvailability).pick({
  tripId: true,
  userId: true,
  date: true,
  available: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export type InsertTrip = z.infer<typeof insertTripSchema>;
export type Trip = typeof trips.$inferSelect;

export type InsertMessage = z.infer<typeof insertMessageSchema>;
export type Message = typeof messages.$inferSelect;

export type InsertVote = z.infer<typeof insertVoteSchema>;
export type Vote = typeof votes.$inferSelect;

export type InsertTripOption = z.infer<typeof insertTripOptionSchema>;
export type TripOption = typeof tripOptions.$inferSelect;

export type InsertDateAvailability = z.infer<typeof insertDateAvailabilitySchema>;
export type DateAvailability = typeof dateAvailability.$inferSelect;

export type TripParticipant = typeof tripParticipants.$inferSelect;
