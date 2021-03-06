from snake_game import SnakeGame
from random import randint
import numpy as np
import tflearn
import math
from tflearn.layers.core import input_data, fully_connected
from tflearn.layers.estimator import regression
from statistics import mean
from collections import Counter


class SnakeNN:
    #Constructor for Neural Net.
    def __init__(self, initial_games=100000, test_games=1000, goal_steps=2000, lr=1e-2, filename='SNN_2.tflearn'):
        self.initial_games = initial_games
        self.test_games = test_games
        self.goal_steps = goal_steps
        self.lr = lr
        self.filename = filename
        self.vectors_and_keys = [
            [[-1, 0], 0],
            [[0, 1], 1],
            [[1, 0], 2],
            [[0, -1], 3]
        ]

    # Initial training data population.
    def initial_population(self):
        training_data = []
        # Play amount of games equal to value of initial games
        for _ in range(self.initial_games):
            # Create new game, for reference of game setup look at snake_game.py start() function.
            game = SnakeGame()
            _, prev_score, snake, food = game.start()
            prev_observation = self.generate_observation(snake, food)
            prev_food_distance = self.get_food_distance(snake, food)
            # Run until amount of moves is equal to value of goal_steps or until failure state is reached.
            for _ in range(self.goal_steps):
                action, game_action = self.generate_action(snake)
                done, score, snake, food = game.step(game_action)
                # If game has ended.
                if done:
                    # Add data from this current attempt to the training data and mark as complete either goal
                    # steps have been reached or snake has died, mark as failure (-1).
                    training_data.append([self.add_action_to_observation(prev_observation, action), -1])
                    break
                # If not done keep playing.
                else:
                    food_distance = self.get_food_distance(snake, food)
                    # If the current score is higher than the previous score or the food is closer add to training data
                    # marked as an optimal move (1).
                    if score > prev_score or food_distance < prev_food_distance:
                        training_data.append([self.add_action_to_observation(prev_observation, action), 1])
                    # Otherwise mark as unoptimal move (0) and add to training data.
                    else:
                        training_data.append([self.add_action_to_observation(prev_observation, action), 0])
                    # Mark previous observation and food distance as latest values.
                    prev_observation = self.generate_observation(snake, food)
                    prev_food_distance = food_distance
        return training_data

    # Generates a random move.
    def generate_action(self, snake):
        action = randint(0, 2) - 1
        return action, self.generate_game_action(snake, action)

    # Generates a move.
    def generate_game_action(self, snake, action):
        snake_direction = self.get_snake_direction_vector(snake)
        new_direction = snake_direction
        if action == -1:
            new_direction = self.turn_vector_to_the_left(snake_direction)
        elif action == 1:
            new_direction = self.turn_vector_to_the_right(snake_direction)
        for pair in self.vectors_and_keys:
            if pair[0] == new_direction.tolist():
                game_action = pair[1]
        return game_action

    # Perform checks for obstacles and calculate angle between food and snake.
    def generate_observation(self, snake, food):
        snake_direction = self.get_snake_direction_vector(snake)
        food_direction = self.get_food_direction_vector(snake, food)
        barrier_left = self.is_direction_blocked(snake, self.turn_vector_to_the_left(snake_direction))
        barrier_front = self.is_direction_blocked(snake, snake_direction)
        barrier_right = self.is_direction_blocked(snake, self.turn_vector_to_the_right(snake_direction))
        angle = self.get_angle(snake_direction, food_direction)
        return np.array([int(barrier_left), int(barrier_front), int(barrier_right), angle])

    # Adds action to observation.
    def add_action_to_observation(self, observation, action):
        return np.append([action], observation)

    # Returns vector equal to snake direction.
    def get_snake_direction_vector(self, snake):
        return np.array(snake[0]) - np.array(snake[1])

    # Returns direction of food, required snake, food and network to be passed in.
    def get_food_direction_vector(self, snake, food):
        return np.array(food) - np.array(snake[0])

    # Returns a normalized vector.
    def normalize_vector(self, vector):
        return vector / np.linalg.norm(vector)

    # Returns food distance.
    def get_food_distance(self, snake, food):
        return np.linalg.norm(self.get_food_direction_vector(snake, food))

    # Check for obstacles.
    def is_direction_blocked(self, snake, direction):
        point = np.array(snake[0]) + np.array(direction)
        return point.tolist() in snake[:-1] or point[0] == 0 or point[1] == 0 or point[0] == 21 or point[1] == 21

    # Returns left vector relative to passed in vector.
    def turn_vector_to_the_left(self, vector):
        return np.array([-vector[1], vector[0]])

    # Returns right vector relative to passed in vector.
    def turn_vector_to_the_right(self, vector):
        return np.array([vector[1], -vector[0]])

    # Returns angle between to vectors.
    def get_angle(self, a, b):
        a = self.normalize_vector(a)
        b = self.normalize_vector(b)
        return math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]) / math.pi

    # Returns the network model.
    def model(self):
        neural_net = input_data(shape=[None, 5, 1], name='input')
        # RelU activation function.
        neural_net = fully_connected(neural_net, 25, activation='relu')
        # Linear activation function.
        neural_net = fully_connected(neural_net, 1, activation='linear')
        # Use TFLearn adam optimizer within regression.
        neural_net = regression(neural_net, optimizer='adam', learning_rate=self.lr, loss='mean_square', name='target')
        model = tflearn.DNN(neural_net, tensorboard_dir='log')
        return model

    # Returns trained model.
    def train_network(self, training_data, model):
        X = np.array([i[0] for i in training_data]).reshape(-1, 5, 1)
        y = np.array([i[1] for i in training_data]).reshape(-1, 1)
        model.fit(X, y, n_epoch=3, shuffle=True, run_id=self.filename)
        model.save(self.filename)
        return model

    # Method to play test games post-learning phase.
    def play_test_games(self, model):
        steps_arr = []
        scores_arr = []
        for _ in range(self.test_games):
            steps = 0
            game_memory = []
            game = SnakeGame()
            _, score, snake, food = game.start()
            prev_observation = self.generate_observation(snake, food)
            for _ in range(self.goal_steps):
                predictions = []
                for action in range(-1, 2):
                    predictions.append(
                        model.predict(self.add_action_to_observation(prev_observation, action).reshape(-1, 5, 1)))
                action = np.argmax(np.array(predictions))
                game_action = self.generate_game_action(snake, action - 1)
                done, score, snake, food = game.step(game_action)
                game_memory.append([prev_observation, action])
                if done:
                    print('-----')
                    print("Steps: " + str(steps))
                    print("Snake: " + str(snake))
                    print("Food: " + str(food))
                    print("Previous Observation: " + str(prev_observation))
                    print("Predictions: " + str(predictions))
                    break
                else:
                    prev_observation = self.generate_observation(snake, food)
                    steps += 1
            steps_arr.append(steps)
            scores_arr.append(score)
        print('Average steps:', mean(steps_arr))
        print(Counter(steps_arr))
        print('Average score:', mean(scores_arr))
        print(Counter(scores_arr))
        print('Highest Score:', max(scores_arr))

    # Used to show the game being played with a generated prediction based on the
    # stuff the network has learned. The game will end if the network reaches 2000 steps or
    # whatever value is assigned to goal_steps.
    def render_game(self, model):
        game = SnakeGame(gui=True)
        _, _, snake, food = game.start()
        prev_observation = self.generate_observation(snake, food)
        for _ in range(self.goal_steps):
            precictions = []
            for action in range(-1, 2):
                precictions.append(
                    model.predict(self.add_action_to_observation(prev_observation, action).reshape(-1, 5, 1)))
            action = np.argmax(np.array(precictions))
            game_action = self.generate_game_action(snake, action - 1)
            done, _, snake, food = game.step(game_action)
            if done:
                break
            else:
                prev_observation = self.generate_observation(snake, food)

    # Call this method to train the neural net, this will not show the game being played.
    # The network will then play a set amount of test games similar to the test method.
    def train(self):
        training_data = self.initial_population()
        nn_model = self.model()
        nn_model = self.train_network(training_data, nn_model)
        self.play_test_games(nn_model)

    # Call this method to visualize the neural network attempting to play snake after learning data has been generated.
    # (Using curses package with custom windows binaries, cross platform curses package should work too,
    # "curses-2.2-cp34-none-win_amd64.whl")
    # Only call this method after learning has been performed at least once, recommended 10000+ games.
    def play_game(self):
        nn_model = self.model()
        nn_model.load(self.filename)
        self.render_game(nn_model)

    # Method used to run a set amount of test games (This is set at the top)
    # Data will be displayed for each game such as score, location of food
    # and previous observation.
    def run_test_games(self):
        nn_model = self.model()
        nn_model.load(self.filename)
        self.play_test_games(nn_model)

# Startup execution/Entry point, comment out methods that do not want to be used.
# Typically only use one method each run.
#
# Comment out all method calls here but the one you would like to run, train must be run before others if
# no data set has been generated previously.
if __name__ == "__main__":
    # SnakeNN().train()
    SnakeNN().play_game()
    # SnakeNN().run_test_games()
