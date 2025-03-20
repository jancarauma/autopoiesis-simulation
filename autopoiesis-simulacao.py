"""
Autopoiesis Simulation: Cellular Automata in Liquid Environment

This script simulates autopoietic systems inspired by the work of Humberto Maturana and Francisco Varela.
It aims to build a model of a self-organizing cellular automata in a liquid-like environment using Pygame for visualization
and Pymunk for physics-based interactions.

Author: Janderson Gomes
Date: October, 2024
License: MIT License

Copyright (c) 2024 Janderson Gomes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import pygame
import pymunk
import pymunk.pygame_util
import random
import math
from enum import Enum
from typing import List, Tuple

COLORS = {
    'background': (10, 10, 30),
    'substrate': (255, 200, 200),  # Rosa claro
    'catalyst': (255, 165, 0),     # Laranja
    'link': (100, 200, 255),       # Azul claro
    'bond': (50, 100, 255),        # Azul escuro
    'text': (255, 255, 255),       # Branco
    'debug': (255, 0, 0)           # Vermelho
}

class ParticleType(Enum):
    SUBSTRATE = 1
    CATALYST = 2
    LINK = 3

class Particle:
    def __init__(self, x: float, y: float, space: pymunk.Space, particle_type: ParticleType):
        self.type = particle_type
        self.radius = 8 if particle_type != ParticleType.CATALYST else 12
        mass = 1
        
        if particle_type == ParticleType.CATALYST:
            vertices = [(-15, -13), (15, -13), (0, 15)]
            moment = pymunk.moment_for_poly(mass, vertices)
            self.body = pymunk.Body(mass, moment)
            self.shape = pymunk.Poly(self.body, vertices)
        else:
            moment = pymunk.moment_for_circle(mass, 0, self.radius)
            self.body = pymunk.Body(mass, moment)
            self.shape = pymunk.Circle(self.body, self.radius)
        
        self.body.position = x, y
        
        # Ajuste das propriedades físicas para melhor comportamento
        self.shape.elasticity = 0.8
        self.shape.friction = 0.7
        self.shape.collision_type = particle_type.value
        
        # Adicionar sensor para links
        if particle_type == ParticleType.LINK:
            sensor_radius = self.radius * 3
            self.sensor = pymunk.Circle(self.body, sensor_radius)
            self.sensor.sensor = True
            self.sensor.collision_type = 10  # Tipo especial para sensor
            space.add(self.sensor)
            
        space.add(self.body, self.shape)
        
        self.connections: List[Particle] = []
        self.max_connections = 2 if particle_type == ParticleType.LINK else 0
        self.age = 0  # Idade da partícula para controle de desintegração

class AutopoiesisSimulation:
    def __init__(self):
        pygame.init()
        self.width = 800
        self.height = 800
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Autopoiesis Simulation - Improved")
        
        # Configuração da fonte para estatísticas
        self.font = pygame.font.Font(None, 24)
        
        # Configuração do espaço físico
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.space.damping = 0.8  # Amortecimento global
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)
        
        # Lista de partículas e ligações
        self.particles: List[Particle] = []
        self.bonds: List[pymunk.Constraint] = []
        
        # Lista temporária para remoção de partículas e ligações
        self.to_remove: List[Tuple[Particle, pymunk.Constraint]] = []
        
        # Estatísticas
        self.stats = {
            'substrate': 0,
            'links': 0,
            'bonds': 0
        }
        
        # Configurar handlers de colisão
        self.setup_collision_handlers()
        
        # Criar partículas iniciais
        self.setup_simulation()
    
    def setup_collision_handlers(self):
        # Catalisador + Substrato
        self.space.add_collision_handler(
            ParticleType.CATALYST.value,
            ParticleType.SUBSTRATE.value
        ).separate = self.handle_catalyst_substrate
        
        # Sensor de Link + Link
        self.space.add_collision_handler(
            10,  # Tipo do sensor
            ParticleType.LINK.value
        ).begin = self.handle_link_detection
    
    def setup_simulation(self):
        # Adicionar catalisador no centro
        catalyst = Particle(
            self.width/2, 
            self.height/2, 
            self.space, 
            ParticleType.CATALYST
        )
        self.particles.append(catalyst)
        
        # Adicionar substrato dentro de um círculo
        num_substrate = 300
        radius = 200  # Raio do círculo de contenção
        for _ in range(num_substrate):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, radius)
            x = self.width / 2 + r * math.cos(angle)
            y = self.height / 2 + r * math.sin(angle)
            substrate = Particle(x, y, self.space, ParticleType.SUBSTRATE)
            self.particles.append(substrate)
    
    def create_link(self, pos: Tuple[float, float]):
        link = Particle(pos[0], pos[1], self.space, ParticleType.LINK)
        self.particles.append(link)
        return link
    
    def create_bond(self, p1: Particle, p2: Particle):
        # Criar mola com propriedades ajustadas
        joint = pymunk.DampedSpring(
            p1.body, p2.body,
            (0, 0), (0, 0),
            rest_length=p1.radius * 2.5,
            stiffness=150,
            damping=1
        )
        self.space.add(joint)
        self.bonds.append(joint)
        p1.connections.append(p2)
        p2.connections.append(p1)
    
    def handle_catalyst_substrate(self, arbiter, space, data):
        if random.random() < 0.15:  # Aumentada probabilidade de reação
            substrate_shape = arbiter.shapes[1]
            nearby_substrates = [
                p for p in self.particles 
                if (p.type == ParticleType.SUBSTRATE and 
                    p.shape != substrate_shape and
                    self.distance(substrate_shape.body.position, p.body.position) < 40)
            ]
            
            if nearby_substrates:
                second_substrate = random.choice(nearby_substrates)
                # Criar link na posição média
                pos = ((substrate_shape.body.position.x + second_substrate.body.position.x) / 2,
                      (substrate_shape.body.position.y + second_substrate.body.position.y) / 2)
                self.create_link(pos)
                
                # Marcar substratos para remoção
                self.to_remove.append((substrate_shape, None))
                self.to_remove.append((second_substrate.shape, None))
        return True
    
    def handle_link_detection(self, arbiter, space, data):
        link_sensor = arbiter.shapes[0]
        link_shape = arbiter.shapes[1]

        p1_candidates = [p for p in self.particles if hasattr(p, 'sensor') and p.sensor == link_sensor]
        p2_candidates = [p for p in self.particles if p.shape == link_shape]

        if p1_candidates and p2_candidates:
            p1 = p1_candidates[0]  # Seleciona o primeiro candidato
            p2 = p2_candidates[0]  # Seleciona o primeiro candidato

            if (p1 != p2 and
                len(p1.connections) < p1.max_connections and
                len(p2.connections) < p2.max_connections and
                p2 not in p1.connections):
                self.create_bond(p1, p2)

        return True

    
    def remove_particle(self, shape):
        try:
            particle = next(p for p in self.particles if p.shape == shape)
            if hasattr(particle, 'sensor'):
                self.space.remove(particle.sensor)
            self.space.remove(particle.shape, particle.body)
            self.particles.remove(particle)
        except StopIteration:
            print("Warning: Attempted to remove a particle that was not found.")
    
    def apply_brownian_motion(self):
        center = pymunk.Vec2d(self.width / 2, self.height / 2)
        confinement_radius = 200  # Raio de confinamento
        attraction_strength = 0.5  # Força de atração

        for particle in self.particles:
            if particle.type != ParticleType.CATALYST:
                # Força de movimento browniano
                force_x = random.gauss(0, 300)
                force_y = random.gauss(0, 300)
                particle.body.apply_force_at_local_point((force_x, force_y), (0, 0))

                # Força de confinamento
                distance_to_center = center.get_distance(particle.body.position)
                if distance_to_center > confinement_radius:
                    direction_to_center = (center - particle.body.position).normalized()
                    confinement_force = direction_to_center * (distance_to_center - confinement_radius) * attraction_strength
                    particle.body.apply_force_at_local_point(confinement_force)
    
    def handle_disintegration(self):
        for particle in list(self.particles):
            if particle.type == ParticleType.LINK:
                particle.age += 1
                if particle.age > 2*500 and random.random() < 0.01:
                    # Remover ligações
                    for connected in particle.connections:
                        connected.connections.remove(particle)
                    # Criar dois substratos
                    pos = particle.body.position
                    offset = 10
                    Particle(pos.x + offset, pos.y, self.space, ParticleType.SUBSTRATE)
                    Particle(pos.x - offset, pos.y, self.space, ParticleType.SUBSTRATE)
                    self.to_remove.append((particle.shape, None))

    def handle_boundary_collision(self):
        center = pymunk.Vec2d(self.width / 2, self.height / 2)
        boundary_radius = 200  # Raio da circunferência

        for particle in self.particles:
            #if particle.type != ParticleType.CATALYST:
                distance_to_center = center.get_distance(particle.body.position)
                if distance_to_center >= boundary_radius - particle.radius:
                    # Calcular a normal e ricochetear
                    normal = (particle.body.position - center).normalized()
                    particle.body.position = center + normal * (boundary_radius - particle.radius)
                    particle.body.velocity = -particle.body.velocity  # Inverter a velocidade para simular ricocheteamento

    def update_stats(self):
        self.stats['substrate'] = len([p for p in self.particles if p.type == ParticleType.SUBSTRATE])
        self.stats['links'] = len([p for p in self.particles if p.type == ParticleType.LINK])
        self.stats['bonds'] = len(self.bonds)
    
    def draw_stats(self):
        y = 10
        for key, value in self.stats.items():
            text = self.font.render(f"{key}: {value}", True, COLORS['text'])
            self.screen.blit(text, (10, y))
            y += 25
    
    def draw_particles(self):
        for particle in self.particles:
            pos = particle.body.position
            if particle.type == ParticleType.SUBSTRATE:
                pygame.draw.circle(self.screen, COLORS['substrate'], 
                                (int(pos.x), int(pos.y)), particle.radius)
            elif particle.type == ParticleType.CATALYST:
                vertices = []
                for v in particle.shape.get_vertices():
                    x = v.rotated(particle.body.angle).x + pos.x
                    y = v.rotated(particle.body.angle).y + pos.y
                    vertices.append((int(x), int(y)))
                pygame.draw.polygon(self.screen, COLORS['catalyst'], vertices)
            elif particle.type == ParticleType.LINK:
                #pygame.draw.circle(self.screen, COLORS['link'], 
                #                (int(pos.x), int(pos.y)), particle.radius)
                rect = pygame.Rect(
                                int(pos.x - particle.radius),
                                int(pos.y - particle.radius),
                                particle.radius * 2,
                                particle.radius * 2
                )
                pygame.draw.rect(self.screen, COLORS['link'], rect)
    
    def draw_bonds(self):
        for bond in self.bonds:
            p1 = bond.a.position
            p2 = bond.b.position
            pygame.draw.line(
                self.screen,
                COLORS['bond'],
                (int(p1.x), int(p1.y)),
                (int(p2.x), int(p2.y)),
                2
            )
    
    def draw_boundary(self):
        # Desenhar a circunferência
        pygame.draw.circle(self.screen, COLORS['debug'], (self.width // 2, self.height // 2), 200, 2)
    
    def distance(self, pos1, pos2):
        return math.sqrt((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2)
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Limpar tela
            self.screen.fill(COLORS['background'])
            
            # Atualizar física
            self.space.step(1/60.0)
            
            # Aplicar movimento browniano
            self.apply_brownian_motion()
            
            # Gerenciar desintegração
            self.handle_disintegration()

            # Gerenciar colisão com a circunferência
            self.handle_boundary_collision()
            
            # Remover partículas e ligações marcadas
            for shape, bond in self.to_remove:
                if shape:
                    self.remove_particle(shape)
                if bond:
                    self.space.remove(bond)
                    self.bonds.remove(bond)
            self.to_remove.clear()
            
            # Desenhar
            self.draw_bonds()
            self.draw_particles()
            self.draw_boundary()  # Desenhar a circunferência
            
            # Atualizar e mostrar estatísticas
            self.update_stats()
            self.draw_stats()
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    sim = AutopoiesisSimulation()
    sim.run()
