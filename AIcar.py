import math
import sys
import neat
import pygame

WIDTH = 1920
HEIGHT = 1080

CAR_SIZE_X = 60    
CAR_SIZE_Y = 60

MAP = 'map3.png'
BORDER_COLOR = (255, 255, 255) # Устанавливаем цвет, соприкосновение с которым считать аварией

current_generation = 0 # Какое поколение

class Car:

    def __init__(self):
        # Загружаем модельку машины
        self.sprite = pygame.image.load('blue_car.png').convert() # Convert Speeds Up A Lot
        self.sprite = pygame.transform.scale(self.sprite, (CAR_SIZE_X, CAR_SIZE_Y))
        self.rotated_sprite = self.sprite 

        self.position = [830, 920] # Устанавливаем стартовую позицию
        self.angle = 0
        self.speed = 0

        self.speed_set = False

        self.center = [self.position[0] + CAR_SIZE_X / 2, self.position[1] + CAR_SIZE_Y / 2] # Считаем координаты центра машины

        self.radars = [] # Список в котором мы храним данные с радаров
        self.drawing_radars = []

        self.alive = True # Разбилась машина или нет

        self.distance = 0
        self.time = 0

    # Отрисовываем наши радары на дополнительном слое поверхности
    def draw(self, screen):
        screen.blit(self.rotated_sprite, self.position)
        self.draw_radar(screen)

    def draw_radar(self, screen):
        for radar in self.radars:
            position = radar[0]
            pygame.draw.line(screen, (0, 255, 0), self.center, position, 1)
            pygame.draw.circle(screen, (0, 255, 0), position, 5)
    #Фиксируем столкновение
    def check_collision(self, game_map):
        self.alive = True
        for point in self.corners:
            if game_map.get_at((int(point[0]), int(point[1]))) == BORDER_COLOR:
                self.alive = False
                break
    #Следим за показаниями с радаров
    def check_radar(self, degree, game_map):
        length = 0
        x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
        y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

        # Перемещаем машину все дальше и дальше, пока не зафиксировано столкновение
        while not game_map.get_at((x, y)) == BORDER_COLOR and length < 300:
            length = length + 1
            x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
            y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

        # Считаем расстояние до краев трассы и добавляем в список
        dist = int(math.sqrt(math.pow(x - self.center[0], 2) + math.pow(y - self.center[1], 2)))
        self.radars.append([(x, y), dist])
    
    def update(self, game_map):
        # Устанавливаем начальную скорость
        if not self.speed_set:
            self.speed = 20
            self.speed_set = True

        # Направление движения по оси X, не даем машине подходить ближе 20px к краю
        self.rotated_sprite = self.rotate_center(self.sprite, self.angle)
        self.position[0] += math.cos(math.radians(360 - self.angle)) * self.speed
        self.position[0] = max(self.position[0], 20)
        self.position[0] = min(self.position[0], WIDTH - 120)

        # Фиксируем расстояние и время после каждого апдейта
        self.distance += self.speed
        self.time += 1
        
        # Тоже что и выше, но для оси Y
        self.position[1] += math.sin(math.radians(360 - self.angle)) * self.speed
        self.position[1] = max(self.position[1], 20)
        self.position[1] = min(self.position[1], WIDTH - 120)

        # Просчитываем новое значение центра машины
        self.center = [int(self.position[0]) + CAR_SIZE_X / 2, int(self.position[1]) + CAR_SIZE_Y / 2]

        # Просчитываем края машины
        length = 0.5 * CAR_SIZE_X
        left_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 30))) * length, self.center[1] + math.sin(math.radians(360 - (self.angle + 30))) * length]
        right_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 150))) * length, self.center[1] + math.sin(math.radians(360 - (self.angle + 150))) * length]
        left_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 210))) * length, self.center[1] + math.sin(math.radians(360 - (self.angle + 210))) * length]
        right_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 330))) * length, self.center[1] + math.sin(math.radians(360 - (self.angle + 330))) * length]
        self.corners = [left_top, right_top, left_bottom, right_bottom]

        # Проверяем столкновения и чистим радары
        self.check_collision(game_map)
        self.radars.clear()

        # Проверяем показания радаров с шагом в 45
        for d in range(-90, 120, 45):
            self.check_radar(d, game_map)

    def get_data(self):
        # Собираем расстояние до границ
        radars = self.radars
        return_values = [0, 0, 0, 0, 0]
        for i, radar in enumerate(radars):
            return_values[i] = int(radar[1] / 30)

        return return_values

    def is_alive(self):
        return self.alive

    def get_reward(self):
        # Награда
        return self.distance / (CAR_SIZE_X / 2)

    def rotate_center(self, image, angle):
        # Ротация головы машины
        rectangle = image.get_rect()
        rotated_image = pygame.transform.rotate(image, angle)
        rotated_rectangle = rectangle.copy()
        rotated_rectangle.center = rotated_image.get_rect().center
        rotated_image = rotated_image.subsurface(rotated_rectangle).copy()
        return rotated_image


def run_simulation(genomes, config):

    nets = []
    cars = []

    # Дисплей pygame с нашими параметрами
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

    # Для каждого поколения создаем свою нейронную сеть
    for i, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

        cars.append(Car())

    # Фонт и карта
    clock = pygame.time.Clock()
    generation_font = pygame.font.SysFont("Arial", 30)
    alive_font = pygame.font.SysFont("Arial", 20)
    game_map = pygame.image.load(MAP).convert()

    global current_generation
    current_generation += 1

    # Переменная для установки времени
    counter = 0

    while True:
        # заканчиваем игру, когда закрываем окно pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)

        # Собираем действия производимые машиной
        for i, car in enumerate(cars):
            output = nets[i].activate(car.get_data())
            choice = output.index(max(output))
            if choice == 0:
                car.angle += 10 # левый поворот
            elif choice == 1:
                car.angle -= 10 # правый
            elif choice == 2:
                if(car.speed - 2 >= 12):
                    car.speed -= 2 # замедление
            else:
                car.speed += 2 # ускорение
        
        # Проверяем не разбилась ли машина
        # Вознаграждаем
        still_alive = 0
        for i, car in enumerate(cars):
            if car.is_alive():
                still_alive += 1
                car.update(game_map)
                genomes[i][1].fitness += car.get_reward()

        if still_alive == 0:
            break

        counter += 1
        if counter == 30 * 40: # Примерно 20 секунд на карту (Нужно изменить на большее значение, если большая или сложная карта)
            break

        # Слой с картой и живыми машинами
        screen.blit(game_map, (0, 0))
        for car in cars:
            if car.is_alive():
                car.draw(screen)
        
        # Отображаем информацию
        text = generation_font.render("Поколение: " + str(current_generation), True, (255,0,0))
        text_rect = text.get_rect()
        text_rect.center = (900, 450)
        screen.blit(text, text_rect)

        text = alive_font.render("Машин на трассе: " + str(still_alive), True, (255, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (900, 490)
        screen.blit(text, text_rect)

        pygame.display.flip()
        clock.tick(60) # 60 FPS

if __name__ == "__main__":
    
    # Подгружаем конфиг модуля NEAT
    config_path = "./config.txt"
    config = neat.config.Config(neat.DefaultGenome,
                                neat.DefaultReproduction,
                                neat.DefaultSpeciesSet,
                                neat.DefaultStagnation,
                                config_path)

    # Создаем поколение и добавляем репорты
    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)
    
    # Устанавливаем максимальное количество поколений
    population.run(run_simulation, 100)
