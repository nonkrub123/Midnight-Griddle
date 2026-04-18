import pygame
from settings import *
from interactive import *

# # 1. Initialize pygame
# pygame.init()

# # 2. Create a display surface (even if you don't use it yet)
# # This allows .convert_alpha() to work.
# screen = pygame.display.set_mode((800, 600))

# # 3. Now you can create your object
# ui = InteractiveObject("button", GamePath.get_ui("20.png"), (0,0))

# print(f"Has 'clickable' tag: {ui.has_tag('clickable')}")
# print(f"Has 'draggable' tag: {ui.has_tag('draggable')}")
import pygame
import sys
from factory import ItemFactory
from group import GrillGroup
from settings import *

def run_test():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Foundation Test: Factory & Movement")
    clock = pygame.time.Clock()

    # 1. Initialize Factory (Foundation Test)
    factory = ItemFactory()
    
    # 2. Setup a Grill Group (Stacking & Snapback Test)
    # Note: Make sure you have a valid image path for the station background
    grill = GrillGroup(
        name="test_grill", 
        image_path=GamePath.get_station("test.png"), 
        pos=(400, 450), 
        max_capacity=3
    )

    # 3. Create a patty using the factory (Image Cache Test)
    # The factory now handles the image and passes it to the object
    patty = factory.create("meat_patty", (100, 100))
    
    # Track the held item for dragging
    held_item = None
    offset_x, offset_y = 0, 0

    print("--- TEST CONTROLS ---")
    print("SPACE: Trigger set_target() to move patty to grill")
    print("CLICK & DRAG: Test snapback and stacking logic")
    print("L: Toggle patty.is_locked (should prevent dragging)")
    print("---------------------")

    while True:
        dt = clock.tick(60) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Test Smooth Movement
                if event.key == pygame.K_SPACE:
                    print("Testing Smooth Move: Sliding to Grill...")
                    patty.set_target(grill.station_block.rect.center, duration=1.0)
                
                # Test Locking logic
                if event.key == pygame.K_l:
                    patty.is_locked = not patty.is_locked
                    print(f"Patty is_locked: {patty.is_locked}")

            # Test Drag and Drop Foundation
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not patty.is_locked and patty.rect.collidepoint(mouse_pos):
                    held_item = patty
                    # Remove from current group to "pick it up"
                    if patty.current_group:
                        patty.current_group.handle_remove(patty)
                    
                    offset_x = patty.rect.centerx - mouse_pos[0]
                    offset_y = patty.rect.centery - mouse_pos[1]

            if event.type == pygame.MOUSEBUTTONUP:
                if held_item:
                    # Test Drop Logic
                    if grill.station_block.rect.collidepoint(mouse_pos):
                        success = grill.handle_drop(held_item, grill.station_block)
                        if not success:
                            grill.handle_snapback(held_item)
                    else:
                        # Test Snapback logic (if dropped in empty space)
                        grill.handle_snapback(held_item)
                    
                    held_item = None

        # Logic Update
        if held_item:
            held_item.rect.center = (mouse_pos[0] + offset_x, mouse_pos[1] + offset_y)
        
        # Update groups (this triggers sprite.update(dt) -> move_to logic)
        grill.update(dt)
        if patty.current_group is None: # Update patty manually if it's being held/not in group
            patty.update(dt)

        # Draw
        screen.fill((30, 30, 30)) # Dark background
        grill.draw(screen)
        if patty.current_group is None:
            screen.blit(patty.image, patty.rect)
            
        pygame.display.flip()

if __name__ == "__main__":
    run_test()