'use client'

import { useEffect, useRef, memo } from 'react'
import * as THREE from 'three'

const AnimatedEarth = memo(() => {
  const mountRef = useRef(null)
  const sceneRef = useRef(null)
  const rendererRef = useRef(null)
  const animationIdRef = useRef(null)

  // Function to create round star texture
  const createStarTexture = () => {
    const canvas = document.createElement('canvas')
    canvas.width = 32
    canvas.height = 32
    const ctx = canvas.getContext('2d')
    
    // Create gradient for round star
    const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16)
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)')
    gradient.addColorStop(0.3, 'rgba(255, 255, 255, 0.8)')
    gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.3)')
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')
    
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 32, 32)
    
    return canvas
  }

  useEffect(() => {
    if (!mountRef.current) return

    // Scene setup
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    )
    camera.position.set(0, 0, 2) // Center the camera

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      alpha: true 
    })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setClearColor(0x000000, 0)
    // Correct color management and tone mapping for accurate brightness
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.NoToneMapping
    renderer.toneMappingExposure = 1
    rendererRef.current = renderer

    // Earth geometry
    const geometry = new THREE.SphereGeometry(0.98, 64,64)
    
    // Earth material with only daymap texture
    const textureLoader = new THREE.TextureLoader()
    
    // Use only the earth daymap texture
    const earthTexture = textureLoader.load('/textures/2k_earth_daymap.jpg')
    earthTexture.colorSpace = THREE.SRGBColorSpace
    
    // Use a physically-based material responsive to light, with minimal glare
    const earthMaterial = new THREE.MeshStandardMaterial({
      map: earthTexture,
      roughness: 0.95,
      metalness: 0
    })
    
    const earth = new THREE.Mesh(geometry, earthMaterial)
    earth.position.set(0, 0, 0) // Ensure Earth is at center
    scene.add(earth)
    
    // Natural lighting setup for centered Earth
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6) // Subtle ambient
    scene.add(ambientLight)
    
    // Main directional light from top-left
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(2, 2, 2) // Adjusted for centered Earth
    scene.add(directionalLight)
    
    // Subtle fill light from opposite side
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.15)
    fillLight.position.set(-2, 1, -2)
    scene.add(fillLight)
    
    // Add stars to the scene
    const starsGeometry = new THREE.BufferGeometry()
    const starsCount = 4000
    const positions = new Float32Array(starsCount * 3)
    
    for (let i = 0; i < starsCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 20
      positions[i + 1] = (Math.random() - 0.5) * 20
      positions[i + 2] = (Math.random() - 0.5) * 20
    }
    
    starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    
    // Create round stars using a custom texture
    const starTexture = new THREE.CanvasTexture(createStarTexture())
    
    const starsMaterial = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.05,
      transparent: true,
      opacity: 0.9,
      map: starTexture,
      blending: THREE.AdditiveBlending
    })
    
    const stars = new THREE.Points(starsGeometry, starsMaterial)
    scene.add(stars)
    
    // Add to DOM
    mountRef.current.appendChild(renderer.domElement)
    
    // Animation loop
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate)
      
      earth.rotation.y += 0.002
      stars.rotation.y += 0.001
      
      renderer.render(scene, camera)
    }
    animate()
    
    // Handle resize
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', handleResize)
    
    // Cleanup
    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current)
      }
      window.removeEventListener('resize', handleResize)
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement)
      }
      renderer.dispose()
    }
  }, [])

  return <div ref={mountRef} className="w-full h-full" />
})

AnimatedEarth.displayName = 'AnimatedEarth'

export default AnimatedEarth 